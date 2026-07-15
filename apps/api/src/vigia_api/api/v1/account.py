from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ...services.account_recovery import AccountRecoveryService
from ...services.auth import AuthService
from ...security.rate_limit import rate_limit
from ...settings import settings

router = APIRouter(tags=["account-recovery"])
auth_service = AuthService()
service = AccountRecoveryService(auth_service.repository)


def _service(request: Request) -> AccountRecoveryService:
    container = getattr(getattr(getattr(request, "app", None), "state", None), "container", None)
    return container.account_recovery_service if container is not None else service


class PasswordResetRequestIn(BaseModel):
    email: str


class PasswordResetConfirmIn(BaseModel):
    token: str
    new_password: str


class EmailVerificationRequestIn(BaseModel):
    email: str | None = None
    user_id: str | None = None


class EmailVerificationConfirmIn(BaseModel):
    token: str


@router.post("/auth/password-reset/request")
def request_password_reset(payload: PasswordResetRequestIn, request: Request) -> dict:
    rate_limit(request, "account.password_reset.request", settings.auth_rate_limit_attempts, settings.auth_rate_limit_window_seconds, email=payload.email)
    return _service(request).request_password_reset(payload.email)


@router.post("/auth/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirmIn, request: Request) -> dict:
    rate_limit(request, "account.password_reset.confirm", settings.auth_rate_limit_attempts, settings.auth_rate_limit_window_seconds)
    try:
        user = _service(request).confirm_password_reset(payload.token, payload.new_password)
        return {"user": user.email}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/auth/email-verification/request")
def request_email_verification(payload: EmailVerificationRequestIn, request: Request) -> dict:
    rate_limit(request, "account.email_verification.request", settings.auth_rate_limit_attempts, settings.auth_rate_limit_window_seconds, email=payload.email, user_id=payload.user_id)
    try:
        token = _service(request).create_email_verification(user_id=payload.user_id, email=payload.email)
        return {"status": "queued", "token": token}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/auth/email-verification/confirm")
def confirm_email_verification(payload: EmailVerificationConfirmIn, request: Request) -> dict:
    rate_limit(request, "account.email_verification.confirm", settings.auth_rate_limit_attempts, settings.auth_rate_limit_window_seconds)
    try:
        user = _service(request).verify_email(payload.token)
        return {"user": user.email}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
