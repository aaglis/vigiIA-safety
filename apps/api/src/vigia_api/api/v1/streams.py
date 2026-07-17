from __future__ import annotations

from typing import Any

import asyncio
import contextlib

from fastapi import APIRouter, Depends, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field

from ...domain.auth import Permission
from ...services.live_stream import LiveStreamService, LiveStreamUnavailable
from ...security.dependencies import get_current_organization_membership, require_permission

router = APIRouter()


class StreamAuthIn(BaseModel):
    action: str | None = None
    path: str | None = None
    query: str | None = None
    ip: str | None = None
    user: str | None = None
    password: str | None = None
    protocol: str | None = None
    id: str | None = None


def _service(request: Request) -> LiveStreamService:
    container = request.app.state.container
    return LiveStreamService(operations_repository=container.operations_repository, settings=container.settings, edge_worker_service=container.edge_worker_service)


def _assert_organization_access(organization_id: str, membership) -> None:
    if membership.organization.id != organization_id:
        raise HTTPException(status_code=403, detail="organization access denied")


@router.get("/organizations/{organization_id}/operations/cameras/{camera_id}/live", dependencies=[Depends(require_permission(Permission.VIEW_DASHBOARD))])
def get_camera_live_ticket(organization_id: str, camera_id: str, request: Request, membership=Depends(get_current_organization_membership)) -> dict[str, Any]:
    _assert_organization_access(organization_id, membership)
    try:
        ticket = _service(request).issue_ticket(organization_id, camera_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="camera not found")
    except LiveStreamUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"camera_id": ticket.camera_id, "protocol": "webrtc-whep", "whep_url": ticket.whep_url, "token": ticket.token, "expires_at": ticket.expires_at.isoformat()}


@router.post("/internal/stream-auth", include_in_schema=False)
def stream_auth(payload: StreamAuthIn, request: Request) -> dict[str, str]:
    """Endpoint chamado pelo MediaMTX do edge, não pelo navegador: sem sessão, só o ticket."""
    if not _service(request).authorize(payload.path or "", payload.query or "", payload.action or "", payload.user, payload.password):
        raise HTTPException(status_code=401, detail="unauthorized")
    return {"status": "ok"}


class DetectedBoxIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: list[float] = Field(min_length=4, max_length=4)


class ViolationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_type: str
    zone_id: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: list[float] = Field(min_length=4, max_length=4)


class FrameAnalysisIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    camera_id: str
    timestamp: str
    boxes: list[DetectedBoxIn] = Field(default_factory=list, max_length=64)
    violations: list[ViolationIn] = Field(default_factory=list, max_length=64)


@router.post("/edge-workers/me/frame-analysis", status_code=202)
def publish_frame_analysis(
    payload: FrameAnalysisIn,
    request: Request,
    x_edge_client_id: str | None = Header(default=None, alias="X-Edge-Client-Id"),
    x_edge_api_key: str | None = Header(default=None, alias="X-Edge-Api-Key"),
) -> dict[str, Any]:
    """O que a CV está vendo no frame atual. Só coordenadas — nenhuma imagem sai do edge.
    Não vira incidente nem é persistido: some se ninguém estiver assistindo."""
    if not x_edge_client_id or not x_edge_api_key:
        raise HTTPException(status_code=401, detail="missing worker credentials")
    container = request.app.state.container
    try:
        config = container.edge_worker_service.config(x_edge_client_id, x_edge_api_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    allowed = {camera.get("id") for camera in config.get("cameras", [])}
    if payload.camera_id not in allowed:
        raise HTTPException(status_code=403, detail="camera not assigned to this worker")
    organization_id = (config.get("worker") or {}).get("organization_id")
    if not organization_id:
        raise HTTPException(status_code=403, detail="worker without organization")
    delivered = container.detection_hub.publish(organization_id, payload.camera_id, payload.model_dump())
    return {"status": "accepted", "delivered_to": delivered}


@router.websocket("/organizations/{organization_id}/operations/cameras/{camera_id}/detections")
async def detections_socket(websocket: WebSocket, organization_id: str, camera_id: str) -> None:
    container = websocket.app.state.container
    service = LiveStreamService(operations_repository=container.operations_repository, settings=container.settings, edge_worker_service=container.edge_worker_service)
    if not service.authorize_detections(organization_id, camera_id, websocket.query_params.get("token")):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    hub = container.detection_hub
    queue = hub.subscribe(organization_id, camera_id)
    try:
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)
    except (WebSocketDisconnect, asyncio.CancelledError, RuntimeError):
        pass
    finally:
        hub.unsubscribe(organization_id, camera_id, queue)
        with contextlib.suppress(RuntimeError):
            await websocket.close()
