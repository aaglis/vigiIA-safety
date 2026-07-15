from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:  # pragma: no cover - optional runtime dependency
    from fastapi import APIRouter, Depends, Header, HTTPException, Request
except Exception:  # pragma: no cover
    if TYPE_CHECKING:
        from fastapi import APIRouter, Depends, Header, HTTPException, Request
    else:
        class HTTPException(Exception):
            def __init__(self, status_code: int, detail: str):
                super().__init__(detail)
                self.status_code = status_code
                self.detail = detail

        class Depends:  # type: ignore[no-redef]
            def __init__(self, dependency: Any):
                self.dependency = dependency

        class Header:  # type: ignore[no-redef]
            def __init__(self, default: Any = None, alias: str | None = None):
                self.default = default
                self.alias = alias

        class Request:  # type: ignore[no-redef]
            pass

        class APIRouter:  # type: ignore[no-redef]
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def post(self, *args: Any, **kwargs: Any):
                def decorator(func):
                    return func

                return decorator

            def get(self, *args: Any, **kwargs: Any):
                def decorator(func):
                    return func

                return decorator
from pydantic import BaseModel, Field

from ...container import edge_worker_service
from ...security.dependencies import get_current_organization_membership, require_permission

router = APIRouter(tags=["edge-workers"])
service = edge_worker_service


def _service(request: Request | None):
    container = getattr(getattr(getattr(request, "app", None), "state", None), "container", None)
    return container.edge_worker_service if container is not None else service


class EdgeWorkerCreateIn(BaseModel):
    organization_id: str
    site_id: str
    name: str
    allowed_camera_ids: list[str] = Field(default_factory=list)


class EdgeWorkerDetectionIn(BaseModel):
    event_id: str | None = None
    organization_id: str | None = None
    site_id: str | None = None
    camera_id: str
    timestamp: str | None = None
    event_type: str = "detection"
    zone_id: str
    confidence: float | None = None
    model_version: str | None = None
    evidence: dict | None = None
    severity: str = "medium"
    summary: str | None = None


def _auth(client_id: str | None, api_key: str | None) -> tuple[str, str]:
    if not client_id or not api_key:
        raise HTTPException(status_code=401, detail="missing edge worker credentials")
    return client_id, api_key


@router.post("/organizations/{organization_id}/edge-workers", status_code=201, dependencies=[Depends(require_permission("workers.register"))])
def register_worker(organization_id: str, payload: EdgeWorkerCreateIn, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    if payload.organization_id != organization_id:
        raise HTTPException(status_code=400, detail="organization_id mismatch")
    worker, api_key = _service(request).register_worker(organization_id, payload.site_id, payload.name, payload.allowed_camera_ids)
    return {"worker": worker.__dict__, "api_key": api_key}


@router.get("/edge-workers/me/config")
def worker_config(request: Request, x_edge_client_id: str | None = Header(default=None, alias="X-Edge-Client-Id"), x_edge_api_key: str | None = Header(default=None, alias="X-Edge-Api-Key")) -> dict:
    client_id, api_key = _auth(x_edge_client_id, x_edge_api_key)
    try:
        return _service(request).config(client_id, api_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/edge-workers/me/heartbeat")
def worker_heartbeat(request: Request, x_edge_client_id: str | None = Header(default=None, alias="X-Edge-Client-Id"), x_edge_api_key: str | None = Header(default=None, alias="X-Edge-Api-Key")) -> dict:
    client_id, api_key = _auth(x_edge_client_id, x_edge_api_key)
    try:
        worker = _service(request).heartbeat(client_id, api_key)
        return {"worker": worker.__dict__}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/edge-workers/me/detections", status_code=201)
def worker_detection(payload: EdgeWorkerDetectionIn, request: Request, x_edge_client_id: str | None = Header(default=None, alias="X-Edge-Client-Id"), x_edge_api_key: str | None = Header(default=None, alias="X-Edge-Api-Key")) -> dict:
    client_id, api_key = _auth(x_edge_client_id, x_edge_api_key)
    try:
        return _service(request).submit_detection(client_id, api_key, payload.model_dump())
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/edge-workers/me/evidence-upload")
def worker_evidence_upload(file_id: str, request: Request, x_edge_client_id: str | None = Header(default=None, alias="X-Edge-Client-Id"), x_edge_api_key: str | None = Header(default=None, alias="X-Edge-Api-Key")) -> dict:
    client_id, api_key = _auth(x_edge_client_id, x_edge_api_key)
    try:
        return _service(request).request_evidence_upload(client_id, api_key, file_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
