from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qs

from .security import decode_jwt, encode_jwt

LIVE_SCHEMES = ("rtsp://", "rtmp://")


class LiveStreamUnavailable(Exception):
    """A câmera não tem fonte ao vivo (ex.: cadastrada como arquivo de vídeo em dev)."""


@dataclass(frozen=True)
class LiveTicket:
    camera_id: str
    path: str
    whep_url: str
    token: str
    expires_at: datetime


def stream_path_for(stream_identifier: str) -> str:
    """Path do MediaMTX embutido na URL RTSP da câmera (`rtsp://host:8554/<path>`)."""
    value = (stream_identifier or "").strip()
    if not any(value.lower().startswith(scheme) for scheme in LIVE_SCHEMES):
        raise LiveStreamUnavailable("camera has no live source")
    remainder = value.split("://", 1)[1]
    path = remainder.split("/", 1)[1].split("?", 1)[0].strip("/") if "/" in remainder else ""
    if not path:
        raise LiveStreamUnavailable("camera stream has no path")
    return path


class LiveStreamService:
    """Emite tickets de curta duração para o navegador consumir o vídeo direto do edge.

    O vídeo NUNCA passa pelo cloud (LGPD + banda): o cloud só assina quem pode ver o quê,
    e o MediaMTX do edge valida o ticket via `authorize` antes de abrir a conexão WebRTC.
    """

    def __init__(self, operations_repository: Any, settings: Any, edge_worker_service: Any | None = None) -> None:
        self.operations_repository = operations_repository
        self.settings = settings
        self.edge_worker_service = edge_worker_service

    def _camera(self, organization_id: str, camera_id: str):
        camera = next((c for c in self.operations_repository.list_cameras(organization_id) if c.id == camera_id), None)
        if camera is None:
            raise KeyError(camera_id)
        return camera

    def issue_ticket(self, organization_id: str, camera_id: str) -> LiveTicket:
        camera = self._camera(organization_id, camera_id)
        path = stream_path_for(camera.stream_identifier)
        ttl = int(self.settings.live_stream_ticket_ttl_seconds)
        token = encode_jwt({"org": organization_id, "cam": camera_id, "path": path, "scope": "live_read"}, self.settings.jwt_secret, ttl)
        base = self.settings.live_stream_public_base_url.rstrip("/")
        return LiveTicket(camera_id=camera_id, path=path, whep_url=f"{base}/{path}/whep?token={token}", token=token, expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl))

    def _authorize_ticket(self, path: str, query: str) -> bool:
        tokens = parse_qs(query or "").get("token") or []
        if not tokens:
            return False
        try:
            claims = decode_jwt(tokens[0], self.settings.jwt_secret)
        except (ValueError, KeyError):
            return False
        return claims.get("scope") == "live_read" and claims.get("path") == path

    def _authorize_worker(self, path: str, user: str | None, password: str | None) -> bool:
        """O edge worker lê a própria câmera com a credencial de máquina que já possui,
        e só as câmeras que lhe foram atribuídas (`allowed_camera_ids`)."""
        if not user or not password or self.edge_worker_service is None:
            return False
        try:
            config = self.edge_worker_service.config(user, password)
        except Exception:
            return False
        for camera in config.get("cameras", []):
            try:
                if stream_path_for(camera.get("stream_identifier", "")) == path:
                    return True
            except LiveStreamUnavailable:
                continue
        return False

    def authorize_detections(self, organization_id: str, camera_id: str, token: str | None) -> bool:
        """O mesmo ticket que abre o vídeo abre as caixas daquela câmera — nada além dela."""
        if not token:
            return False
        try:
            claims = decode_jwt(token, self.settings.jwt_secret)
        except (ValueError, KeyError):
            return False
        return claims.get("scope") == "live_read" and claims.get("org") == organization_id and claims.get("cam") == camera_id

    def authorize(self, path: str, query: str, action: str, user: str | None = None, password: str | None = None) -> bool:
        """Chamado pelo MediaMTX (authHTTPAddress) a cada tentativa de leitura."""
        if action not in ("read", "playback"):
            return False
        return self._authorize_ticket(path, query) or self._authorize_worker(path, user, password)
