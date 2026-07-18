from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from ...domain.incidents import IncidentStatus, parse_detection_event
from ...container import incident_repository
from ...services.incidents import incident_to_dict
from ...security.csrf import require_csrf
from ...security.dependencies import get_current_user, require_permission
from ...security.origin import validate_origin_or_referer

router = APIRouter(tags=["incidents"])

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


def _repository(request: Request | None):
    container = getattr(getattr(getattr(request, "app", None), "state", None), "container", None)
    return container.incident_repository if container is not None else incident_repository


def _paginate(items: list[Any], limit: int = DEFAULT_LIMIT, offset: int = 0) -> dict:
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    total = len(items)
    sliced = items[offset: offset + limit]
    return {"items": sliced, "page_info": {"limit": limit, "offset": offset, "total": total, "has_next": offset + limit < total}}


class DetectionEventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str
    event_id: str | None = None
    site_id: str | None = None
    camera_id: str
    zone_id: str
    worker_id: str | None = None
    event_type: str = "detection"
    severity: str
    timestamp: str | None = None
    confidence: float | None = None
    model_version: str | None = None
    evidence: dict | None = None
    summary: str | None = None
    metadata: dict = Field(default_factory=dict)


class IncidentReasonIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1)


def _status_response(incident):
    return incident_to_dict(incident)


@router.post("/organizations/{organization_id}/incidents:ingest", status_code=201, dependencies=[Depends(require_csrf)])
def ingest_detection_event(organization_id: str, payload: DetectionEventIn, request: Request) -> dict:
    validate_origin_or_referer(request)
    if payload.organization_id != organization_id:
        raise HTTPException(status_code=400, detail="organization_id mismatch")
    incident = _repository(request).create_from_detection(parse_detection_event(payload.model_dump()))
    return _status_response(incident)


@router.get("/organizations/{organization_id}/incidents", dependencies=[Depends(require_permission("incidents.read"))])
def list_incidents(organization_id: str, request: Request, limit: int = DEFAULT_LIMIT, offset: int = 0, status: str | None = None, site_id: str | None = None, camera_id: str | None = None, zone_id: str | None = None, severity: str | None = None, created_from: str | None = None, created_to: str | None = None) -> dict:
    repo = _repository(request)
    created_from_dt = datetime.fromisoformat(created_from.replace("Z", "+00:00")) if created_from else None
    created_to_dt = datetime.fromisoformat(created_to.replace("Z", "+00:00")) if created_to else None
    filters = {"status": status, "site_id": site_id, "camera_id": camera_id, "zone_id": zone_id, "severity": severity, "created_from": created_from_dt, "created_to": created_to_dt}
    if hasattr(repo, "list_filtered"):
        items = repo.list_filtered(organization_id, limit=limit, offset=offset, **filters)
        total = repo.count_filtered(organization_id, **filters) if hasattr(repo, "count_filtered") else len(repo.list_filtered(organization_id, **filters))
        page = [incident_to_dict(incident) for incident in items]
        return {"items": page, "page_info": {"limit": max(1, min(limit, MAX_LIMIT)), "offset": max(0, offset), "total": total, "has_next": max(0, offset) + max(1, min(limit, MAX_LIMIT)) < total}}
    items = repo.list_by_organization(organization_id)
    return _paginate([incident_to_dict(incident) for incident in items], limit=limit, offset=offset)


@router.get("/organizations/{organization_id}/incidents/{incident_id}", dependencies=[Depends(require_permission("incidents.read"))])
def get_incident(organization_id: str, incident_id: str, request: Request) -> dict:
    try:
        return incident_to_dict(_repository(request).get(organization_id, incident_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="incident not found") from exc


@router.post("/organizations/{organization_id}/incidents/{incident_id}:acknowledge", dependencies=[Depends(require_permission("incidents.acknowledge")), Depends(require_csrf)])
def acknowledge_incident(organization_id: str, incident_id: str, request: Request, current_user=Depends(get_current_user)) -> dict:
    validate_origin_or_referer(request)
    try:
        return incident_to_dict(_repository(request).transition(organization_id, incident_id, IncidentStatus.ACKNOWLEDGED, current_user.user.id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="incident not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/organizations/{organization_id}/incidents/{incident_id}:resolve", dependencies=[Depends(require_permission("incidents.resolve")), Depends(require_csrf)])
def resolve_incident(organization_id: str, incident_id: str, payload: IncidentReasonIn, request: Request, current_user=Depends(get_current_user)) -> dict:
    validate_origin_or_referer(request)
    try:
        return incident_to_dict(_repository(request).transition(organization_id, incident_id, IncidentStatus.RESOLVED, current_user.user.id, reason=payload.reason))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="incident not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400 if "requires reason" in str(exc) else 409, detail=str(exc)) from exc


@router.post("/organizations/{organization_id}/incidents/{incident_id}:dismiss", dependencies=[Depends(require_permission("incidents.dismiss")), Depends(require_csrf)])
def dismiss_incident(organization_id: str, incident_id: str, payload: IncidentReasonIn, request: Request, current_user=Depends(get_current_user)) -> dict:
    validate_origin_or_referer(request)
    try:
        return incident_to_dict(_repository(request).transition(organization_id, incident_id, IncidentStatus.DISMISSED, current_user.user.id, reason=payload.reason))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="incident not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400 if "requires reason" in str(exc) else 409, detail=str(exc)) from exc


@router.get("/organizations/{organization_id}/incidents/{incident_id}/audit-log", dependencies=[Depends(require_permission("audit.read"))])
def incident_audit_log(organization_id: str, incident_id: str, request: Request, limit: int = DEFAULT_LIMIT, offset: int = 0, action: str | None = None) -> dict:
    repo = _repository(request)
    items = repo.audit_logs(organization_id, incident_id)
    if action:
        items = [entry for entry in items if entry.action == action]
    return _paginate([entry.__dict__ for entry in items], limit=limit, offset=offset)
