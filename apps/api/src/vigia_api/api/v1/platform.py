from __future__ import annotations

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
from pydantic import BaseModel

from ...security.csrf import require_csrf
from ...security.dependencies import get_current_user, require_platform_role
from ...security.origin import validate_origin_or_referer
from ...services.auth import AuthService
from ...services.platform_admin import PlatformAdminService

router = APIRouter(tags=["platform-admin"])
auth_service = AuthService()
service = PlatformAdminService(auth_service.repository)
DEFAULT_LIMIT = 50
MAX_LIMIT = 100


def _service(request: Request) -> PlatformAdminService:
    container = getattr(getattr(getattr(request, "app", None), "state", None), "container", None)
    return container.platform_admin_service if container is not None else service


def _paginate(items: list[Any], limit: int = DEFAULT_LIMIT, offset: int = 0) -> dict:
    limit = max(1, min(limit, MAX_LIMIT))
    offset = max(0, offset)
    total = len(items)
    return {"items": items[offset: offset + limit], "page_info": {"limit": limit, "offset": offset, "total": total, "has_next": offset + limit < total}}


class OrganizationIn(BaseModel):
    name: str
    legal_name: str
    tax_id: str
    plan: str | None = None
    leader_email: str | None = None
    created_by_user_id: str


@router.post("/platform/organizations", dependencies=[Depends(require_csrf)])
def create_organization(payload: OrganizationIn, request: Request, current_user=Depends(require_platform_role("platform_owner", "platform_admin"))) -> dict:
    validate_origin_or_referer(request)
    try:
        data = payload.model_dump()
        data["created_by_user_id"] = current_user.user.id
        organization = _service(request).create_organization(**data)
        return {"organization": organization.__dict__}
    except (PermissionError, KeyError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/platform/organizations")
def list_organizations(request: Request, current_user=Depends(require_platform_role("platform_owner", "platform_admin", "platform_support"))) -> dict:
    return {"items": _service(request).list_organizations()}


@router.post("/platform/organizations/{organization_id}/suspend", dependencies=[Depends(require_csrf)])
def suspend_organization(organization_id: str, request: Request, current_user=Depends(require_platform_role("platform_owner", "platform_admin"))) -> dict:
    validate_origin_or_referer(request)
    try:
        return {"organization": _service(request).suspend_organization(organization_id, current_user.user.id).__dict__}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="organization not found") from exc


@router.post("/platform/organizations/{organization_id}/reactivate", dependencies=[Depends(require_csrf)])
def reactivate_organization(organization_id: str, request: Request, current_user=Depends(require_platform_role("platform_owner", "platform_admin"))) -> dict:
    validate_origin_or_referer(request)
    try:
        return {"organization": _service(request).reactivate_organization(organization_id, current_user.user.id).__dict__}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="organization not found") from exc


@router.get("/platform/audit-logs")
def list_audit_logs(request: Request, current_user=Depends(require_platform_role("platform_owner", "platform_admin", "platform_support")), limit: int = DEFAULT_LIMIT, offset: int = 0, action: str | None = None) -> dict:
    items = [log.__dict__ for log in _service(request).audit_logs]
    if action:
        items = [item for item in items if item.get("action") == action]
    return _paginate(items, limit=limit, offset=offset)
