from __future__ import annotations

import os
from urllib.parse import urlparse
from typing import Any, cast
from pydantic_settings import BaseSettings


def _is_weak_secret(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    weak_markers = {"dev-only", "change-me", "example", "password", "vigia", "todo", "replace-me", "test"}
    return len(normalized) < 20 or any(marker in normalized for marker in weak_markers)


def _is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    placeholder_markers = {"dev-only", "example", "placeholder", "todo"}
    return any(marker in normalized for marker in placeholder_markers)


def _is_https_origin(value: str) -> bool:
    return value.startswith("https://") and "localhost" not in value and "127.0.0.1" not in value


def _uses_demo_credentials(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    return normalized in {
        "admin@vigia.local",
        "change-me-dev",
        "dev-only",
        "vigia-local",
        "org-demo",
        "user-dev",
    }


class Settings(BaseSettings):
    app_env: str = "dev"
    app_name: str = "VigIA API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://dev-only:dev-only@postgres:5432/vigia"
    repository_backend: str = "memory"
    redis_url: str = "redis://redis:6379/0"
    rate_limit_backend: str = "auto"
    jwt_secret: str = "dev-only-jwt-secret-change-me"
    refresh_token_secret: str = "dev-only-refresh-secret-change-me"
    access_token_ttl_seconds: int = 900
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    csrf_enabled: bool = True
    csrf_cookie_name: str = "csrf_token"
    csrf_header_name: str = "x-csrf-token"
    csrf_cookie_path: str = "/"
    refresh_cookie_name: str = "refresh_token"
    access_cookie_name: str = "access_token"
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 60
    auth_rate_limit_attempts: int = 10
    auth_rate_limit_window_seconds: int = 60
    sensitive_rate_limit_attempts: int = 5
    sensitive_rate_limit_window_seconds: int = 300
    evidence_bucket_name: str = "vigia-evidence-private"
    evidence_presigned_url_ttl_seconds: int = 300
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None
    # Endpoint alcançável pelo NAVEGADOR. As URLs assinadas de download precisam ser
    # assinadas com o host que o browser acessa (ex.: localhost:9000), e não com o
    # host interno da rede docker (minio:9000). Sem isso, cai no s3_endpoint_url.
    s3_public_endpoint_url: str | None = None
    allow_internal_s3_endpoint: bool = False
    minio_access_key: str = "dev-only"
    minio_secret_key: str = "dev-only"
    resend_api_key: str = ""
    notification_from: str = "alerts@vigia.local"
    live_stream_public_base_url: str = "http://localhost:8889"
    live_stream_ticket_ttl_seconds: int = 60
    frame_analysis_config_cache_seconds: float = 2.0
    incident_notification_enabled: bool = True
    incident_notification_mode: str = "mock"  # mock|resend
    incident_notification_recipients: list[str] = ["ops@vigia.local"]
    incident_notification_severity_threshold: str = "high"
    scheduler_notifications_interval_seconds: int = 30
    scheduler_offline_workers_interval_seconds: int = 60
    scheduler_evidence_retention_interval_seconds: int = 86400
    scheduler_evidence_retention_confirm: bool = False
    scheduler_lock_ttl_seconds: int = 120
    scheduler_organization_ids: list[str] = []
    edge_worker_api_key: str = "dev-only"
    edge_worker_client_id: str = "dev-client-id"
    metrics_token: str = ""

    def _apply_env_aliases(self, data: dict[str, Any]) -> dict[str, Any]:
        if "minio_access_key" not in data:
            alias = os.environ.get("S3_ACCESS_KEY_ID")
            if alias:
                data["minio_access_key"] = alias
        if "minio_secret_key" not in data:
            alias = os.environ.get("S3_SECRET_ACCESS_KEY")
            if alias:
                data["minio_secret_key"] = alias
        return data

    def _allows_internal_s3_endpoint(self) -> bool:
        if not self.allow_internal_s3_endpoint or not self.s3_endpoint_url:
            return False
        parsed = urlparse(self.s3_endpoint_url)
        return parsed.scheme == "http" and parsed.hostname == "minio"

    def validate_for_environment(self) -> None:
        environment = self.app_env.lower()
        if environment in {"production", "staging"}:
            if self.repository_backend.lower() == "memory":
                raise ValueError(f"repository_backend must not be memory in {environment}")
            if self.rate_limit_backend.lower() == "memory":
                raise ValueError(f"rate_limit_backend must not be memory in {environment}")
            if not self.cookie_secure:
                raise ValueError(f"cookie_secure must be enabled in {environment}")
            if not self.allowed_origins or not all(_is_https_origin(origin) for origin in self.allowed_origins):
                raise ValueError(f"allowed_origins must contain only https origins in {environment}")
            if not self.metrics_token or _is_weak_secret(self.metrics_token):
                raise ValueError(f"metrics_token must be configured with a strong non-default value in {environment}")
            secret_fields = {
                "jwt_secret": self.jwt_secret,
                "refresh_token_secret": self.refresh_token_secret,
                "minio_access_key": self.minio_access_key,
                "minio_secret_key": self.minio_secret_key,
                "edge_worker_api_key": self.edge_worker_api_key,
                "edge_worker_client_id": self.edge_worker_client_id,
                "metrics_token": self.metrics_token,
            }
            config_fields = {
                "database_url": self.database_url,
                "redis_url": self.redis_url,
                "incident_notification_recipients": ",".join(self.incident_notification_recipients),
                "s3_endpoint_url": self.s3_endpoint_url or "",
                "evidence_bucket_name": self.evidence_bucket_name,
            }
            if self.incident_notification_enabled and self.incident_notification_mode.lower() == "resend":
                secret_fields["resend_api_key"] = self.resend_api_key
                config_fields["notification_from"] = self.notification_from
            for field_name, value in secret_fields.items():
                if _is_weak_secret(value):
                    raise ValueError(f"{field_name} must be configured with a strong non-default value in {environment}")
            for field_name, value in config_fields.items():
                if _is_placeholder(value):
                    raise ValueError(f"{field_name} must be configured for {environment}")
            if _uses_demo_credentials(self.database_url) or _uses_demo_credentials(self.redis_url):
                raise ValueError(f"demo credentials are not allowed in {environment}")
            if self.s3_endpoint_url is None or not (self.s3_endpoint_url.startswith("https://") or self._allows_internal_s3_endpoint()):
                raise ValueError(f"s3_endpoint_url must be a real https endpoint in {environment}")
            if _is_placeholder(self.evidence_bucket_name):
                raise ValueError(f"evidence_bucket_name must be configured for {environment}")
            if self.incident_notification_enabled and self.incident_notification_mode.lower() == "resend":
                demo_fields = {
                    "notification_from": self.notification_from,
                    "incident_notification_recipients": ",".join(self.incident_notification_recipients),
                }
                for field_name, value in demo_fields.items():
                    if _uses_demo_credentials(value):
                        raise ValueError(f"{field_name} must not use demo credentials in {environment}")

    def __init__(self, **data: Any):  # type: ignore[override]
        env = os.environ.get("APP_ENV") or os.environ.get("VIGIA_ENV")
        if env and "app_env" not in data:
            data["app_env"] = env
        data = self._apply_env_aliases(data)
        super().__init__(**cast(Any, data))
        self.validate_for_environment()


settings = Settings()
