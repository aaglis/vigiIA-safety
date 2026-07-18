from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
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


class EdgeWorkerHeartbeatIn(BaseModel):
    """Espelha o heartbeat do worker (`build_heartbeat`). `status` carrega a telemetria:
    latência de inferência, fila pendente, último erro e `inactive_rules` — as regras que
    o modelo carregado não consegue avaliar."""

    client_id: str | None = None
    organization_id: str | None = None
    site_id: str | None = None
    sent_at: str | None = None
    version: str | None = None
    status: dict[str, Any] = Field(default_factory=dict)


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


@router.get("/organizations/{organization_id}/edge-workers", dependencies=[Depends(require_permission("workers.manage"))])
def list_workers(organization_id: str, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    """Inventário de workers da organização, com a última telemetria de cada um.

    Nunca devolve `api_key_hash`: a chave só existe em claro no instante do registro.
    """
    if membership.organization.id != organization_id:
        raise HTTPException(status_code=403, detail="organization access denied")
    workers = _service(request).list_workers(organization_id)
    return {
        "items": [
            {
                "id": w.id,
                "organization_id": w.organization_id,
                "site_id": w.site_id,
                "name": w.name,
                "client_id": w.client_id,
                "allowed_camera_ids": w.allowed_camera_ids,
                "status": w.status.value,
                "last_heartbeat_at": w.last_heartbeat_at.isoformat() if w.last_heartbeat_at else None,
                "last_telemetry": w.last_telemetry,
            }
            for w in workers
        ]
    }


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
def worker_heartbeat(payload: EdgeWorkerHeartbeatIn | None = None, request: Request = None, x_edge_client_id: str | None = Header(default=None, alias="X-Edge-Client-Id"), x_edge_api_key: str | None = Header(default=None, alias="X-Edge-Api-Key")) -> dict:
    client_id, api_key = _auth(x_edge_client_id, x_edge_api_key)
    try:
        # O `status` do heartbeat era descartado: o worker mandava latência, fila e
        # regras inativas, e nada disso chegava a quem opera.
        worker = _service(request).heartbeat(client_id, api_key, telemetry=payload.status if payload else None)
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
