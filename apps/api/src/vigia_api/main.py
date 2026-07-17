from __future__ import annotations

from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request, Response

from .api.v1.account import router as account_router
from .api.v1.auth import router as auth_router
from .api.v1.edge_workers import router as edge_workers_router
from .api.v1.evidence import router as evidence_router
from .api.v1.health import router as health_router
from .api.v1.incidents import router as incidents_router
from .api.v1.invites import router as invites_router
from .api.v1.members import router as members_router
from .api.v1.operations import router as operations_router
from .api.v1.streams import router as streams_router
from .api.v1.platform import router as platform_router
from .container import AppContainer, build_container
from .observability import observe_request, set_request_id, snapshot_metrics
from .settings import Settings, settings


def create_app(config: Settings | None = None, container: AppContainer | None = None) -> FastAPI:
    config = config or settings
    container = container or build_container(config)
    app = FastAPI(title=config.app_name)
    app.state.container = container
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"] if not config.csrf_enabled else ["content-type", config.csrf_header_name, "authorization"],
    )
    app.include_router(health_router, prefix=config.api_v1_prefix)
    app.include_router(auth_router, prefix=config.api_v1_prefix)
    app.include_router(account_router, prefix=config.api_v1_prefix)
    app.include_router(invites_router, prefix=config.api_v1_prefix)
    app.include_router(members_router, prefix=config.api_v1_prefix)
    app.include_router(edge_workers_router, prefix=config.api_v1_prefix)
    app.include_router(evidence_router, prefix=config.api_v1_prefix)
    app.include_router(operations_router, prefix=config.api_v1_prefix)
    app.include_router(streams_router, prefix=config.api_v1_prefix)
    app.include_router(platform_router, prefix=config.api_v1_prefix)
    app.include_router(incidents_router, prefix=config.api_v1_prefix)

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid4().hex
        token = set_request_id(request_id)
        start = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            observe_request(request.url.path, status_code, (perf_counter() - start) * 1000)
            set_request_id(None, token=token)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"message": "VigIA API skeleton"}

    @app.get("/metrics")
    def metrics(x_metrics_token: str | None = Header(default=None, alias="X-Metrics-Token")) -> dict:
        if config.app_env.lower() in {"staging", "production"}:
            if not x_metrics_token or x_metrics_token != config.metrics_token:
                raise HTTPException(status_code=401, detail="metrics token required")
        return snapshot_metrics()

    return app


app = create_app()
