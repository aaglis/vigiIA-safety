from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ...security.csrf import require_csrf
from ...security.dependencies import get_current_organization_membership, get_current_user, require_permission
from ...security.origin import validate_origin_or_referer
from ...security.rate_limit import rate_limit
from ...settings import settings
from ...services.auth import AuthService
from ...services.invites import InviteService

router = APIRouter(tags=["invites"])
auth_service = AuthService()
service = InviteService(auth_service.repository)


def _service(request: Request) -> InviteService:
    container = getattr(getattr(getattr(request, "app", None), "state", None), "container", None)
    return container.invite_service if container is not None else service


def _public_user(user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "platform_role": user.platform_role.value,
        "is_active": user.is_active,
        "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
        "created_at": user.created_at.isoformat(),
    }


class InviteIn(BaseModel):
    email: str
    role: str


class AcceptInviteIn(BaseModel):
    token: str
    email: str
    full_name: str
    password: str | None = None


@router.post("/organizations/{organization_id}/invites", dependencies=[Depends(require_permission("org.members.invite")), Depends(require_csrf)])
def create_invite(organization_id: str, payload: InviteIn, request: Request, membership=Depends(get_current_organization_membership), current_user=Depends(get_current_user)) -> dict:
    validate_origin_or_referer(request)
    rate_limit(request, "invites.create", settings.sensitive_rate_limit_attempts, settings.sensitive_rate_limit_window_seconds, email=payload.email, user_id=current_user.user.id)
    try:
        invite, token = _service(request).create_invite(organization_id, payload.email, payload.role, current_user.user.id, membership.role)
        return {"invite": invite.__dict__, "token": token}
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/organizations/{organization_id}/invites", dependencies=[Depends(require_permission("org.members.manage"))])
def list_invites(organization_id: str, request: Request) -> dict:
    return {"items": [invite.__dict__ for invite in _service(request).list_invites(organization_id)]}


@router.post("/organizations/{organization_id}/invites/{invite_id}:resend", dependencies=[Depends(require_permission("org.members.invite")), Depends(require_csrf)])
def resend_invite(organization_id: str, invite_id: str, request: Request) -> dict:
    validate_origin_or_referer(request)
    rate_limit(request, "invites.resend", settings.sensitive_rate_limit_attempts, settings.sensitive_rate_limit_window_seconds)
    invite_service = _service(request)
    invite = invite_service.repository.invites[invite_id]
    if invite.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="invite not found")
    return {"token": invite_service.resend_invite(invite_id)}


@router.post("/organizations/{organization_id}/invites/{invite_id}:revoke", dependencies=[Depends(require_permission("org.members.manage")), Depends(require_csrf)])
def revoke_invite(organization_id: str, invite_id: str, request: Request) -> dict:
    validate_origin_or_referer(request)
    rate_limit(request, "invites.revoke", settings.sensitive_rate_limit_attempts, settings.sensitive_rate_limit_window_seconds)
    invite_service = _service(request)
    invite = invite_service.repository.invites[invite_id]
    if invite.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="invite not found")
    return {"invite": invite_service.revoke_invite(invite_id).__dict__}


@router.post("/invites/accept", dependencies=[Depends(require_csrf)])
def accept_invite(payload: AcceptInviteIn, request: Request) -> dict:
    validate_origin_or_referer(request)
    rate_limit(request, "invites.accept", settings.sensitive_rate_limit_attempts, settings.sensitive_rate_limit_window_seconds, email=payload.email)
    try:
        user = _service(request).accept_invite(**payload.model_dump())
        return {"user": _public_user(user)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
