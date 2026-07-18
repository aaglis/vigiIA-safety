from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from pydantic import BaseModel

from ...security.csrf import require_csrf
from ...security.dependencies import get_current_organization_membership, get_current_user, require_permission
from ...security.origin import validate_origin_or_referer
from ...security.permissions import has_permission
from ...services.auth import AuthService

router = APIRouter(tags=["members"])
service = AuthService()


def _service(request: Request) -> AuthService:
    container = getattr(getattr(getattr(request, "app", None), "state", None), "container", None)
    return container.auth_service if container is not None else service


def _ensure_owner_guard(request: Request, organization_id: str, user_id: str, target_role: str | None, target_active: bool | None) -> None:
    auth = _service(request)
    memberships = auth.list_organization_memberships(organization_id)
    active_owners = [m for m in memberships if m["role"] == "org_owner" and m["active"]]
    current = next((m for m in memberships if m["user"]["id"] == user_id), None)
    if current is None:
        raise HTTPException(status_code=404, detail="membership not found")
    if current["role"] == "org_owner" and (target_role is not None and target_role != "org_owner" or target_active is False):
        if len(active_owners) <= 1:
            raise HTTPException(status_code=409, detail="last active org_owner cannot be changed")


class MemberPatchIn(BaseModel):
    role: str | None = None
    active: bool | None = None


@router.get("/organizations/{organization_id}/members", dependencies=[Depends(require_permission("org.members.manage"))])
def list_members(organization_id: str, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    if membership.organization.id != organization_id:
        raise HTTPException(status_code=403, detail="organization access denied")
    return {"items": _service(request).list_organization_memberships(organization_id)}


@router.patch("/organizations/{organization_id}/members/{user_id}", dependencies=[Depends(require_permission("org.members.manage")), Depends(require_csrf)])
def patch_member(organization_id: str, user_id: str, payload: MemberPatchIn, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    validate_origin_or_referer(request)
    if membership.organization.id != organization_id:
        raise HTTPException(status_code=403, detail="organization access denied")
    if payload.role is not None and payload.role != membership.role:
        if not has_permission(membership.role, "org.roles.manage"):
            raise HTTPException(status_code=403, detail="permission denied")
    _ensure_owner_guard(request, organization_id, user_id, payload.role, payload.active)
    try:
        return {"member": _service(request).update_organization_membership(organization_id, user_id, role=payload.role, active=payload.active)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="membership not found") from exc


@router.delete("/organizations/{organization_id}/members/{user_id}", dependencies=[Depends(require_permission("org.members.manage")), Depends(require_csrf)])
def delete_member(organization_id: str, user_id: str, request: Request, membership=Depends(get_current_organization_membership)) -> dict:
    validate_origin_or_referer(request)
    if membership.organization.id != organization_id:
        raise HTTPException(status_code=403, detail="organization access denied")
    _ensure_owner_guard(request, organization_id, user_id, None, False)
    try:
        return {"member": _service(request).deactivate_organization_membership(organization_id, user_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="membership not found") from exc
