from __future__ import annotations

from dataclasses import dataclass
import socket
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen

from .settings import settings


@dataclass(frozen=True)
class DatabaseCheckResult:
    ok: bool
    configured: bool
    dialect: str
    sanitized_url: str
    error: str | None = None


@dataclass(frozen=True)
class DependencyCheckResult:
    ok: bool
    configured: bool
    sanitized_url: str
    error: str | None = None


def get_database_url() -> str:
    return settings.database_url


def sanitize_database_url(url: str | None) -> str:
    if not url:
        return "<not-configured>"
    parsed = urlparse(url)
    if not parsed.scheme:
        return "<invalid-database-url>"
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    if parsed.username:
        netloc = f"{parsed.username}:***@{netloc}" if parsed.password else f"{parsed.username}@{netloc}"
    elif parsed.password:
        netloc = f":***@{netloc}"
    return urlunparse((parsed.scheme, netloc, parsed.path or "", parsed.params or "", parsed.query or "", parsed.fragment or ""))


def is_postgres_url(url: str | None) -> bool:
    if not url:
        return False
    return url.startswith("postgresql://") or url.startswith("postgresql+psycopg://")


def _probe_sqlite_like(url: str) -> bool:
    return url.startswith("sqlite:")


def check_database_connection(settings_obj: object = settings, timeout_seconds: int = 2) -> DatabaseCheckResult:
    url = getattr(settings_obj, "database_url", None)
    configured = bool(url)
    dialect = urlparse(url).scheme if url else ""
    sanitized = sanitize_database_url(url)
    if not configured:
        return DatabaseCheckResult(ok=False, configured=False, dialect=dialect, sanitized_url=sanitized, error="database_url not configured")

    if _probe_sqlite_like(url):
        return DatabaseCheckResult(ok=True, configured=True, dialect=dialect, sanitized_url=sanitized)

    probe = getattr(settings_obj, "database_probe", None)
    if callable(probe):
        try:
            ok = bool(probe(timeout_seconds=timeout_seconds))
            return DatabaseCheckResult(ok=ok, configured=True, dialect=dialect, sanitized_url=sanitized, error=None if ok else "database probe failed")
        except Exception as exc:  # pragma: no cover - defensive
            return DatabaseCheckResult(ok=False, configured=True, dialect=dialect, sanitized_url=sanitized, error=str(exc))

    try:
        from sqlalchemy import create_engine, text  # type: ignore[import-not-found]

        engine = create_engine(url, connect_args={"connect_timeout": timeout_seconds}, pool_pre_ping=True, future=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        return DatabaseCheckResult(ok=True, configured=True, dialect=dialect, sanitized_url=sanitized)
    except Exception as exc:  # pragma: no cover - depends on runtime services
        return DatabaseCheckResult(ok=False, configured=True, dialect=dialect, sanitized_url=sanitized, error=str(exc))

    return DatabaseCheckResult(ok=False, configured=True, dialect=dialect, sanitized_url=sanitized, error="database driver not installed or probe unavailable")


def _check_dependency_url(settings_obj: object, attr_name: str, probe_attr: str) -> DependencyCheckResult:
    url = getattr(settings_obj, attr_name, None)
    sanitized = sanitize_database_url(url)
    configured = bool(url)
    if not configured:
        return DependencyCheckResult(ok=False, configured=False, sanitized_url=sanitized, error=f"{attr_name} not configured")
    probe = getattr(settings_obj, probe_attr, None)
    if callable(probe):
        try:
            ok = bool(probe())
            return DependencyCheckResult(ok=ok, configured=True, sanitized_url=sanitized, error=None if ok else f"{attr_name} probe failed")
        except Exception as exc:  # pragma: no cover - defensive
            return DependencyCheckResult(ok=False, configured=True, sanitized_url=sanitized, error=str(exc))
    return DependencyCheckResult(ok=False, configured=True, sanitized_url=sanitized, error=f"{attr_name} probe unavailable")


def check_redis_connection(settings_obj: object = settings) -> DependencyCheckResult:
    result = _check_dependency_url(settings_obj, "redis_url", "redis_probe")
    if result.ok or not result.configured or result.error != "redis_url probe unavailable":
        return result

    url = getattr(settings_obj, "redis_url", None)
    parsed = urlparse(url)
    host = str(parsed.hostname or "localhost")
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=2) as sock:
            sock.sendall(b"*1\r\n$4\r\nPING\r\n")
            response = sock.recv(16)
        ok = response.startswith(b"+PONG")
        return DependencyCheckResult(ok=ok, configured=True, sanitized_url=result.sanitized_url, error=None if ok else "redis ping failed")
    except Exception as exc:  # pragma: no cover - depends on runtime services
        return DependencyCheckResult(ok=False, configured=True, sanitized_url=result.sanitized_url, error=str(exc))


def check_minio_connection(settings_obj: object = settings) -> DependencyCheckResult:
    url = getattr(settings_obj, "s3_endpoint_url", None) or getattr(settings_obj, "minio_endpoint", None)
    sanitized = sanitize_database_url(url)
    configured = bool(url)
    if not configured:
        return DependencyCheckResult(ok=False, configured=False, sanitized_url=sanitized, error="minio endpoint not configured")
    probe = getattr(settings_obj, "minio_probe", None)
    if callable(probe):
        try:
            ok = bool(probe())
            return DependencyCheckResult(ok=ok, configured=True, sanitized_url=sanitized, error=None if ok else "minio probe failed")
        except Exception as exc:  # pragma: no cover - defensive
            return DependencyCheckResult(ok=False, configured=True, sanitized_url=sanitized, error=str(exc))
    try:
        health_url = f"{url.rstrip('/')}/minio/health/live"
        with urlopen(health_url, timeout=2) as response:  # nosec B310 - dev health probe URL comes from settings
            ok = 200 <= response.status < 300
        return DependencyCheckResult(ok=ok, configured=True, sanitized_url=sanitized, error=None if ok else "minio health probe failed")
    except Exception as exc:  # pragma: no cover - depends on runtime services
        return DependencyCheckResult(ok=False, configured=True, sanitized_url=sanitized, error=str(exc))
