from __future__ import annotations

import logging
import secrets
from typing import TYPE_CHECKING, Any

try:  # pragma: no cover - optional runtime dependency
    from fastapi import HTTPException, Request
except Exception:  # pragma: no cover
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str) -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    if TYPE_CHECKING:
        from fastapi import Request
    else:
        Request = Any  # type: ignore[assignment]

from ..settings import settings

logger = logging.getLogger(__name__)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def validate_csrf_token(cookie_token: str | None, header_token: str | None) -> bool:
    return bool(cookie_token and header_token and secrets.compare_digest(cookie_token, header_token))


def set_csrf_cookie(response, token: str | None = None) -> str:
    token = token or generate_csrf_token()
    response.set_cookie(settings.csrf_cookie_name, token, httponly=False, secure=settings.cookie_secure, samesite=settings.cookie_samesite, path=settings.csrf_cookie_path)
    return token


def require_csrf(request: Request) -> None:
    if not settings.csrf_enabled:
        return
    # resolved dynamically to support settings overrides
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    header_token = request.headers.get(settings.csrf_header_name)
    if validate_csrf_token(cookie_token, header_token):
        return
    logger.warning("suspicious csrf attempt ip=%s path=%s", request.client.host if request.client else None, request.url.path)
    raise HTTPException(status_code=403, detail="csrf validation failed")
