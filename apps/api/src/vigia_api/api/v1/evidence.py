from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from ...domain.evidence import EvidencePurgeError
from ...security.csrf import require_csrf
from ...security.dependencies import get_current_user, require_permission
from ...security.origin import validate_origin_or_referer
from ...services.evidence import EvidenceService

router = APIRouter(tags=["evidence"])
service = EvidenceService()

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


def _service(request: Request | None) -> EvidenceService:
    container = getattr(getattr(getattr(request, "app", None), "state", None), "container", None)
    return container.evidence_service if container is not None else service


def _paginate(items: list[Any], limit: int = DEFAULT_LIMIT, offset: int = 0) -> dict:
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    total = len(items)
    sliced = items[offset: offset + limit]
    return {"items": sliced, "page_info": {"limit": limit, "offset": offset, "total": total, "has_next": offset + limit < total}}


class EvidenceRegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_type: str
    size: int
    uploaded_by: str
    source: str = "user"


class EvidenceRetentionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata_days: int | None = None
    snapshot_days: int | None = None
    clip_days: int | None = None
    audit_log_days: int | None = None
    actor_user_id: str | None = None
    reason: str | None = None


class EvidencePurgeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: bool = False
    actor_user_id: str | None = None
    reason: str | None = None


@router.post("/organizations/{organization_id}/incidents/{incident_id}/evidence/{file_id}:download-url", dependencies=[Depends(require_permission("evidence.read")), Depends(require_csrf)])
def download_url(organization_id: str, incident_id: str, file_id: str, request: Request, current_user=Depends(get_current_user)) -> dict:
    validate_origin_or_referer(request)
    try:
        return _service(request).get_download_url(organization_id, incident_id, file_id, current_user.user.id, permission_checked=True)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="evidence not found") from exc


@router.post("/organizations/{organization_id}/incidents/{incident_id}/evidence/{file_id}:upload-url", dependencies=[Depends(require_permission("incidents.write")), Depends(require_csrf)])
def upload_url(organization_id: str, incident_id: str, file_id: str, payload: EvidenceRegisterIn, request: Request, current_user=Depends(get_current_user)) -> dict:
    validate_origin_or_referer(request)
    return _service(request).request_upload_url(organization_id, incident_id, file_id, current_user.user.id)


@router.get("/organizations/{organization_id}/evidence/retention", dependencies=[Depends(require_permission("audit.read"))])
def retention_policy(organization_id: str, request: Request) -> dict:
    return _service(request).get_retention_policy(organization_id).__dict__


@router.put("/organizations/{organization_id}/evidence/retention", dependencies=[Depends(require_permission("audit.read")), Depends(require_csrf)])
def update_retention_policy(organization_id: str, payload: EvidenceRetentionIn, request: Request, current_user=Depends(get_current_user)) -> dict:
    validate_origin_or_referer(request)
    return _service(request).set_retention_policy(organization_id, payload.metadata_days, payload.snapshot_days, payload.clip_days, payload.audit_log_days, actor_user_id=current_user.user.id, reason=payload.reason).__dict__


@router.get("/organizations/{organization_id}/evidence/purge-preview", dependencies=[Depends(require_permission("audit.read"))])
def purge_preview(organization_id: str, request: Request, limit: int = DEFAULT_LIMIT, offset: int = 0) -> dict:
    items = _service(request).preview_expired_evidence(organization_id)
    return _paginate(items, limit=limit, offset=offset)


@router.get("/organizations/{organization_id}/evidence", dependencies=[Depends(require_permission("evidence.read"))])
def list_evidence(organization_id: str, request: Request, limit: int = DEFAULT_LIMIT, offset: int = 0, incident_id: str | None = None) -> dict:
    service_obj = _service(request)
    items = service_obj.list_evidence(organization_id, incident_id=incident_id, limit=limit, offset=offset)
    total = service_obj.count_evidence(organization_id, incident_id=incident_id) if hasattr(service_obj, "count_evidence") else len(service_obj.list_evidence(organization_id, incident_id=incident_id, limit=None, offset=0))
    page_limit = max(1, min(limit, MAX_LIMIT))
    page_offset = max(0, offset)
    return {"items": [item.__dict__ for item in items], "page_info": {"limit": page_limit, "offset": page_offset, "total": total, "has_next": page_offset + page_limit < total}}


@router.get("/organizations/{organization_id}/evidence/audit-logs", dependencies=[Depends(require_permission("audit.read"))])
def list_audit_logs(organization_id: str, request: Request, limit: int = DEFAULT_LIMIT, offset: int = 0, incident_id: str | None = None, file_id: str | None = None, action: str | None = None) -> dict:
    items = _service(request).list_audit_logs(organization_id, incident_id=incident_id, file_id=file_id, action=action, limit=limit, offset=offset)
    return _paginate([item.__dict__ for item in items], limit=limit, offset=offset)


@router.post("/organizations/{organization_id}/evidence/purge", dependencies=[Depends(require_permission("audit.read")), Depends(require_csrf)])
def purge_expired(organization_id: str, payload: EvidencePurgeIn, request: Request, current_user=Depends(get_current_user)) -> dict:
    validate_origin_or_referer(request)
    try:
        return _service(request).purge_expired_evidence(organization_id, confirm=payload.confirm, actor_user_id=current_user.user.id, reason=payload.reason)
    except EvidencePurgeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
