from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:  # pragma: no cover - optional runtime dependency
    from fastapi import Cookie, Depends, HTTPException, Request
except Exception:  # pragma: no cover
    if TYPE_CHECKING:
        from fastapi import Cookie, Depends, HTTPException, Request
    else:
        class HTTPException(Exception):
            def __init__(self, status_code: int, detail: str):
                super().__init__(detail)
                self.status_code = status_code
                self.detail = detail

        class Depends:  # type: ignore[no-redef]
            def __init__(self, dependency: Any):
                self.dependency = dependency

        class Cookie:  # type: ignore[no-redef]
            def __init__(self, default: Any = None, alias: str | None = None):
                self.default = default
                self.alias = alias

        class Request:  # type: ignore[no-redef]
            pass

from ..services.auth import AuthService
from ..settings import settings
from .permissions import has_permission

auth_service = AuthService()


def get_auth_service(request: Request) -> AuthService:
    container = getattr(getattr(getattr(request, "app", None), "state", None), "container", None)
    return container.auth_service if container is not None else auth_service


def get_current_user(request: Request, access_token: str | None = Cookie(default=None, alias=settings.access_cookie_name)):
    if not access_token:
        raise HTTPException(status_code=401, detail="missing access token")
    return get_auth_service(request).get_current_user(access_token)


def _resolve_organization_id(organization_id: str | None = None, org_id: str | None = None) -> str:
    resolved = organization_id or org_id
    if not resolved:
        raise HTTPException(status_code=400, detail="organization_id required")
    return resolved


def get_current_organization_membership(organization_id: str | None = None, org_id: str | None = None, user=Depends(get_current_user)):
    resolved_org_id = _resolve_organization_id(organization_id=organization_id, org_id=org_id)
    for membership in user.memberships:
        if membership.organization.id == resolved_org_id:
            return membership
    raise HTTPException(status_code=403, detail="organization access denied")


def require_permission(permission: str):
    def dependency(organization_id: str | None = None, org_id: str | None = None, membership=Depends(get_current_organization_membership)):
        if not has_permission(membership.role, permission):
            raise HTTPException(status_code=403, detail="permission denied")
        return membership

    return dependency


def require_platform_role(*roles: str):
    def dependency(user=Depends(get_current_user)):
        if user.user.platform_role.value not in roles:
            raise HTTPException(status_code=403, detail="platform permission denied")
        return user

    return dependency
