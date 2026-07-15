from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import WorkerConfig
from .detector import FrameInput


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


def build_frame_source(config: WorkerConfig) -> FrameSource:
    source_type = config.edge_source_type
    if source_type == "mock":
        return MockFrameSource(config)
    if source_type in {"image", "video"}:
        if not config.edge_source_uri:
            raise FrameSourceError(f"EDGE_SOURCE_URI is required for source type {source_type}")
        return LocalFileFrameSource(config, config.edge_source_uri, source_type)
    if source_type == "rtsp":
        raise FrameSourceError("EDGE_SOURCE_TYPE=rtsp is experimental and requires a future OpenCV/stream adapter")
    raise FrameSourceError("EDGE_SOURCE_TYPE must be mock, image, video, or rtsp")
