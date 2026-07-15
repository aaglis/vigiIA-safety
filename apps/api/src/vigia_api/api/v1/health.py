from typing import TYPE_CHECKING, Any

try:  # pragma: no cover - optional runtime dependency
    from fastapi import APIRouter, Header, HTTPException, Request
except Exception:  # pragma: no cover
    if TYPE_CHECKING:
        from fastapi import APIRouter, Header, HTTPException, Request
    else:
        class APIRouter:  # type: ignore[no-redef]
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def get(self, *args: Any, **kwargs: Any):
                def decorator(func):
                    return func

                return decorator

        class Header:  # type: ignore[no-redef]
            def __init__(self, default: Any = None, alias: str | None = None):
                self.default = default
                self.alias = alias

        class HTTPException(Exception):  # type: ignore[no-redef]
            def __init__(self, status_code: int, detail: str):
                super().__init__(detail)
                self.status_code = status_code
                self.detail = detail

        class Request:  # type: ignore[no-redef]
            pass

from ... import db as db_module
from ...observability import snapshot_metrics
from ...settings import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    db = db_module.check_database_connection()
    redis = db_module.check_redis_connection()
    minio = db_module.check_minio_connection()
    dependencies = {"database": db.__dict__, "redis": redis.__dict__, "minio": minio.__dict__}
    status = "ok" if all(item["ok"] for item in dependencies.values()) else "degraded"
    return {"status": status, "dependencies": dependencies}


@router.get("/readiness")
def readiness() -> dict[str, object]:
    return health()


@router.get("/metrics")
def metrics(request: Request, x_metrics_token: str | None = Header(default=None, alias="X-Metrics-Token")) -> dict[str, object]:
    container = getattr(getattr(getattr(request, "app", None), "state", None), "container", None)
    config = container.settings if container is not None else settings
    if config.app_env.lower() in {"staging", "production"}:
        if not x_metrics_token or x_metrics_token != config.metrics_token:
            raise HTTPException(status_code=401, detail="metrics token required")
    return snapshot_metrics()
