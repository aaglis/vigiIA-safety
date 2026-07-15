from __future__ import annotations

import os
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
    placeholder_markers = {"dev-only", "example", "placeholder", "todo", "smtp.dev.local"}
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
    minio_access_key: str = "dev-only"
    minio_secret_key: str = "dev-only"
    smtp_host: str = "smtp.dev.local"
    smtp_user: str = "dev-only"
    smtp_password: str = "dev-only"
    smtp_from: str = "alerts@vigia.local"
    incident_notification_enabled: bool = True
    incident_notification_mode: str = "mock"  # mock|smtp
    incident_notification_recipients: list[str] = ["ops@vigia.local"]
    incident_notification_severity_threshold: str = "high"
    edge_worker_api_key: str = "dev-only"
    edge_worker_client_id: str = "dev-client-id"
    metrics_token: str = ""

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
                "smtp_user": self.smtp_user,
                "smtp_password": self.smtp_password,
                "edge_worker_api_key": self.edge_worker_api_key,
                "edge_worker_client_id": self.edge_worker_client_id,
                "metrics_token": self.metrics_token,
            }
            config_fields = {
                "database_url": self.database_url,
                "redis_url": self.redis_url,
                "smtp_host": self.smtp_host,
                "incident_notification_recipients": ",".join(self.incident_notification_recipients),
                "s3_endpoint_url": self.s3_endpoint_url or "",
                "evidence_bucket_name": self.evidence_bucket_name,
            }
            for field_name, value in secret_fields.items():
                if _is_weak_secret(value):
                    raise ValueError(f"{field_name} must be configured with a strong non-default value in {environment}")
            for field_name, value in config_fields.items():
                if _is_placeholder(value):
                    raise ValueError(f"{field_name} must be configured for {environment}")
            if _uses_demo_credentials(self.database_url) or _uses_demo_credentials(self.redis_url):
                raise ValueError(f"demo credentials are not allowed in {environment}")
            if self.s3_endpoint_url is None or not self.s3_endpoint_url.startswith("https://"):
                raise ValueError(f"s3_endpoint_url must be a real https endpoint in {environment}")
            if _is_placeholder(self.evidence_bucket_name):
                raise ValueError(f"evidence_bucket_name must be configured for {environment}")
            demo_fields = {
                "smtp_from": self.smtp_from,
                "incident_notification_recipients": ",".join(self.incident_notification_recipients),
            }
            for field_name, value in demo_fields.items():
                if _uses_demo_credentials(value):
                    raise ValueError(f"{field_name} must not use demo credentials in {environment}")

    def __init__(self, **data: Any):  # type: ignore[override]
        env = os.environ.get("APP_ENV") or os.environ.get("VIGIA_ENV")
        if env and "app_env" not in data:
            data["app_env"] = env
        super().__init__(**cast(Any, data))
        self.validate_for_environment()


settings = Settings()
