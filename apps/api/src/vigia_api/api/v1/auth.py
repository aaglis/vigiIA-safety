from __future__ import annotations

import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ...services.auth import AuthService
from ...settings import settings
from ...security.csrf import require_csrf, set_csrf_cookie
from ...security.origin import validate_origin_or_referer
from ...security.rate_limit import rate_limit

router = APIRouter(tags=["auth"])
service = AuthService()
logger = logging.getLogger(__name__)


def _service(request: Request) -> AuthService:
    container = getattr(getattr(getattr(request, "app", None), "state", None), "container", None)
    return container.auth_service if container is not None else service


class LoginIn(BaseModel):
    email: str
    password: str


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(settings.access_cookie_name, access_token, httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite, path="/")
    response.set_cookie(settings.refresh_cookie_name, refresh_token, httponly=True, secure=settings.cookie_secure, samesite=settings.cookie_samesite, path="/api/v1/auth/refresh")


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.access_cookie_name, path="/")
    response.delete_cookie(settings.refresh_cookie_name, path="/api/v1/auth/refresh")


@router.post("/auth/login")
def login(payload: LoginIn, request: Request, response: Response) -> dict:
    validate_origin_or_referer(request)
    rate_limit(request, "auth.login", settings.login_rate_limit_attempts, settings.login_rate_limit_window_seconds, email=payload.email)
    try:
        auth_service = _service(request)
        tokens, _, me = auth_service.login(payload.email, payload.password, user_agent=request.headers.get("user-agent"), ip_address=request.client.host if request.client else None)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    set_csrf_cookie(response)
    return {"tokens": {"access_token": tokens.access_token, "token_type": tokens.token_type, "access_token_expires_in": tokens.access_token_expires_in}, "me": auth_service.me(tokens.access_token), "user": me.user.email}


@router.post("/auth/refresh", dependencies=[Depends(require_csrf)])
def refresh(request: Request, response: Response, refresh_token: str | None = Cookie(default=None, alias=settings.refresh_cookie_name)) -> dict:
    validate_origin_or_referer(request)
    rate_limit(request, "auth.refresh", settings.auth_rate_limit_attempts, settings.auth_rate_limit_window_seconds)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="missing refresh token")
    try:
        tokens, _, _ = _service(request).refresh(refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    set_csrf_cookie(response)
    return {"tokens": {"access_token": tokens.access_token, "token_type": tokens.token_type, "access_token_expires_in": tokens.access_token_expires_in}}


@router.post("/auth/logout", dependencies=[Depends(require_csrf)])
def logout(request: Request, response: Response, refresh_token: str | None = Cookie(default=None, alias=settings.refresh_cookie_name)) -> dict:
    validate_origin_or_referer(request)
    if refresh_token:
        _service(request).logout(refresh_token)
    _clear_auth_cookies(response)
    set_csrf_cookie(response)
    return {"status": "ok"}


@router.get("/auth/me")
def me(request: Request, access_token: str | None = Cookie(default=None, alias=settings.access_cookie_name)) -> dict:
    if not access_token:
        raise HTTPException(status_code=401, detail="missing access token")
    try:
        return _service(request).me(access_token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid access token") from exc
