from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from ..settings import settings

try:  # pragma: no cover - optional runtime dependency
    import redis
except Exception:  # pragma: no cover
    redis = None  # type: ignore[assignment]

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

logger = logging.getLogger(__name__)


def _hash_part(value: str | None) -> str:
    value = value or "unknown"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _scope_key(action: str, ip: str | None = None, email: str | None = None, user_id: str | None = None) -> str:
    parts = [action, f"ip:{_hash_part(ip)}"]
    if email:
        parts.append(f"email:{_hash_part(email.lower())}")
    if user_id:
        parts.append(f"user:{_hash_part(user_id)}")
    return "rate-limit:" + ":".join(parts)


@dataclass
class _Window:
    count: int
    started_at: float


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, _Window] = {}

    def allow(self, key: str, limit: int, window_seconds: int, now: float | None = None) -> bool:
        now = datetime.now(timezone.utc).timestamp() if now is None else now
        window = self._windows.get(key)
        if not window or now - window.started_at >= window_seconds:
            self._windows[key] = _Window(count=1, started_at=now)
            return True
        if window.count >= limit:
            return False
        window.count += 1
        return True


class RedisRateLimiter:
    def __init__(self, redis_url: str | None = None) -> None:
        self.redis_url = redis_url or settings.redis_url
        if redis is None:
            raise RuntimeError("redis client is not installed")
        self._client = redis.Redis.from_url(self.redis_url, decode_responses=True)

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        pipe = self._client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds, nx=True)
        count, _ = pipe.execute()
        return int(count) <= limit


rate_limiter = InMemoryRateLimiter()


def _configured_backend() -> str:
    backend = settings.rate_limit_backend.lower().strip()
    if backend not in {"auto", "memory", "redis"}:
        return "auto"
    return backend


def _get_limiter():
    backend = _configured_backend()
    environment = settings.app_env.lower()
    if backend == "memory" or settings.app_env.lower() == "test":
        return rate_limiter
    if backend == "redis" or backend == "auto":
        if redis is None:
            if environment in {"production", "staging"} or backend == "redis":
                raise RuntimeError("redis client is required for configured rate limit backend")
            return rate_limiter
        try:
            return RedisRateLimiter(settings.redis_url)
        except Exception:
            if environment in {"production", "staging"} or backend == "redis":
                raise
            logger.warning("rate limit redis unavailable; falling back to memory")
            return rate_limiter
    return rate_limiter


def rate_limit(request: Request, action: str, limit: int, window_seconds: int, *, email: str | None = None, user_id: str | None = None) -> None:
    client = getattr(request, "client", None)
    ip = client.host if client and getattr(client, "host", None) else "unknown"
    key = _scope_key(action, ip=ip, email=email, user_id=user_id)
    limiter = _get_limiter()
    try:
        allowed = limiter.allow(key, limit, window_seconds)
    except Exception:
        backend = _configured_backend()
        environment = settings.app_env.lower()
        if backend == "redis" or environment in {"production", "staging"}:
            raise
        logger.warning("rate limit backend failed; falling back to memory action=%s path=%s", action, getattr(getattr(request, "url", None), "path", "unknown"))
        allowed = rate_limiter.allow(key, limit, window_seconds)
    if allowed:
        return
    logger.warning("rate limit exceeded action=%s ip=%s path=%s", action, ip, getattr(getattr(request, "url", None), "path", "unknown"))
    raise HTTPException(status_code=429, detail="too many requests")
