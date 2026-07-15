from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

try:  # pragma: no cover - optional runtime dependency
    from fastapi import APIRouter, Depends, HTTPException, Request
except Exception:  # pragma: no cover
    if TYPE_CHECKING:
        from fastapi import APIRouter, Depends, HTTPException, Request
    else:
        class HTTPException(Exception):
            def __init__(self, status_code: int, detail: str):
                super().__init__(detail)
                self.status_code = status_code
                self.detail = detail

        class Depends:  # type: ignore[no-redef]
            def __init__(self, dependency: Any):
                self.dependency = dependency

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
    items = repo.list_filtered(organization_id, status=status, site_id=site_id, camera_id=camera_id, zone_id=zone_id, severity=severity, created_from=created_from_dt, created_to=created_to_dt) if hasattr(repo, "list_filtered") else repo.list_by_organization(organization_id)
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
