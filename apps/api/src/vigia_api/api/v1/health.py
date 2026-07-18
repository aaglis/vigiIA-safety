from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

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
