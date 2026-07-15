from __future__ import annotations

import logging
from urllib.parse import urlparse
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


def _origin_host(origin: str) -> str:
    parsed = urlparse(origin)
    return f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""


def is_allowed_origin(origin: str | None) -> bool:
    return bool(origin and _origin_host(origin) in settings.allowed_origins)


def validate_origin_or_referer(request: Request) -> None:
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    candidate = origin or (_origin_host(referer) if referer else None)
    if candidate and is_allowed_origin(candidate):
        return
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    logger.warning("suspicious origin/referer attempt ip=%s path=%s origin=%s referer=%s", request.client.host if request.client else None, request.url.path, origin, referer)
    raise HTTPException(status_code=403, detail="origin validation failed")
