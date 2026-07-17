from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import WorkerConfig
from .detector import FrameInput
from .events import utc_now
from .telemetry import structured_log

_VIDEO_SUFFIXES = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")
# Fontes ao vivo reconectam quando caem; arquivo de vídeo termina no fim.
_LIVE_SOURCE_TYPES = frozenset({"rtsp", "rtmp", "http"})


def classify_source_type(uri: str) -> str:
    """Deriva o tipo de fonte a partir do stream_identifier vindo do cadastro da câmera."""
    low = (uri or "").lower()
    path = low.rsplit("?", 1)[0].rsplit("#", 1)[0]
    if low.startswith("rtsp://"):
        return "rtsp"
    if low.startswith("rtmp://"):
        return "rtmp"
    if low.startswith(("http://", "https://")):
        return "video" if path.endswith(_VIDEO_SUFFIXES) else "http"
    return "video"  # arquivo local ou file:// — cv2.VideoCapture abre igual


@dataclass(frozen=True)
class SourceSelection:
    source_type: str = "mock"
    source_uri: str | None = None
    frame_interval_seconds: float = 0.0
    max_frames: int | None = None


class FrameSourceError(RuntimeError):
    pass


class FrameSource:
    def frames(self):
        raise NotImplementedError


class MockFrameSource(FrameSource):
    source_type = "mock"

    def __init__(self, config: WorkerConfig) -> None:
        self.config = config

    def frames(self):
        yield FrameInput(camera_id=self.config.camera_id, site_id=self.config.site_id, organization_id=self.config.organization_id, timestamp="1970-01-01T00:00:00Z", worker_id=self.config.edge_worker_id, metadata={"source_type": "mock"})


class LocalFileFrameSource(FrameSource):
    def __init__(self, config: WorkerConfig, source_uri: str, source_type: str) -> None:
        self.config = config
        self.source_type = source_type
        self.path = Path(source_uri)

    def frames(self):
        if not self.path.exists():
            raise FrameSourceError(f"source not found: {self.path}")
        if self.path.is_dir():
            files = sorted(p for p in self.path.iterdir() if p.is_file())
        else:
            files = [self.path]
        if not files:
            raise FrameSourceError(f"source is empty: {self.path}")
        for index, file_path in enumerate(files):
            yield FrameInput(camera_id=self.config.camera_id, site_id=self.config.site_id, organization_id=self.config.organization_id, timestamp=f"1970-01-01T00:00:{index:02d}Z", worker_id=self.config.edge_worker_id, image_bytes=file_path.read_bytes(), metadata={"source_type": self.source_type, "source_path": str(file_path), "frame_index": index})


class Cv2VideoSource(FrameSource):
    """Decodifica frames de um arquivo de vídeo ou stream RTSP/HTTP via OpenCV.

    Em produção o mesmo código abre uma câmera RTSP ao vivo; em dev abre o arquivo
    de vídeo cadastrado como stream_identifier. OpenCV é importado sob demanda para
    o pacote continuar importável (e testável) sem as dependências pesadas de CV.
    """

    def __init__(self, config: WorkerConfig, source_uri: str, source_type: str = "video") -> None:
        self.config = config
        self.source_uri = source_uri
        self.source_type = source_type

    def _target(self) -> str:
        if self.source_uri.startswith("file://"):
            return self.source_uri[len("file://"):]
        return self.source_uri

    @property
    def is_live(self) -> bool:
        """Stream ao vivo (câmera): queda é transitória e deve reconectar.
        Arquivo de vídeo: o fim é legítimo e encerra o ciclo."""
        return self.source_type in _LIVE_SOURCE_TYPES

    def _read_frames(self, cv2: Any, cap: Any):
        stride = max(1, int(self.config.edge_video_frame_stride))
        index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                return
            if index % stride == 0:
                ok_enc, buffer = cv2.imencode(".jpg", frame)
                image_bytes = buffer.tobytes() if ok_enc else None
                height, width = frame.shape[:2]
                yield FrameInput(
                    camera_id=self.config.camera_id,
                    site_id=self.config.site_id,
                    organization_id=self.config.organization_id,
                    timestamp=utc_now(),
                    worker_id=self.config.edge_worker_id,
                    image_bytes=image_bytes,
                    frame=frame,
                    width=int(width),
                    height=int(height),
                    metadata={"source_type": self.source_type, "frame_index": index},
                )
            index += 1

    def frames(self):
        try:
            import cv2  # type: ignore
        except Exception as exc:  # pragma: no cover - depende de ambiente com OpenCV
            raise FrameSourceError("OpenCV (opencv-python) é necessário para fontes de vídeo/RTSP") from exc
        backoff = max(0.1, float(self.config.edge_reconnect_backoff_seconds))
        max_backoff = max(backoff, float(self.config.edge_reconnect_max_backoff_seconds))
        while True:
            cap = cv2.VideoCapture(self._target())
            if not cap.isOpened():
                cap.release()
                if not self.is_live:
                    raise FrameSourceError(f"não foi possível abrir a fonte de vídeo: {self.source_uri}")
                structured_log("edge_worker.source_unavailable", camera_id=self.config.camera_id, site_id=self.config.site_id, organization_id=self.config.organization_id, result="failed", source_type=self.source_type, retry_in_seconds=backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                continue
            backoff = max(0.1, float(self.config.edge_reconnect_backoff_seconds))
            try:
                yield from self._read_frames(cv2, cap)
            finally:
                cap.release()
            if not self.is_live:
                return
            # Stream ao vivo caiu/pausou: reconecta em vez de encerrar o worker.
            structured_log("edge_worker.source_reconnect", camera_id=self.config.camera_id, site_id=self.config.site_id, organization_id=self.config.organization_id, result="retry", source_type=self.source_type, retry_in_seconds=backoff)
            time.sleep(backoff)


def build_frame_source(config: WorkerConfig, stream_override: str | None = None) -> FrameSource:
    """Constrói a fonte de frames.

    stream_override (stream_identifier vindo do /me/config) tem prioridade sobre o env:
    a câmera cadastrada dirige o worker. Sem ele, cai no EDGE_SOURCE_TYPE/URI do ambiente.
    """
    source_uri = stream_override or config.edge_source_uri
    source_type = classify_source_type(stream_override) if stream_override else config.edge_source_type
    if source_type == "mock":
        return MockFrameSource(config)
    if source_type in {"rtsp", "rtmp", "http", "video"}:
        if not source_uri:
            raise FrameSourceError(f"EDGE_SOURCE_URI is required for source type {source_type}")
        return Cv2VideoSource(config, source_uri, source_type)
    if source_type == "image":
        if not source_uri:
            raise FrameSourceError("EDGE_SOURCE_URI is required for source type image")
        return LocalFileFrameSource(config, source_uri, "image")
    raise FrameSourceError("EDGE_SOURCE_TYPE must be mock, image, video, rtsp, rtmp, or http")
