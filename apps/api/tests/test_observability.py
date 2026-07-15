import unittest
from typing import Callable, cast

from vigia_api.container import build_container
from vigia_api.observability import build_event, increment_metric, sanitize_for_log, snapshot_metrics
from vigia_api.settings import settings

try:
    from fastapi.testclient import TestClient  # type: ignore[import-not-found]

    from vigia_api.main import create_app
except Exception:  # pragma: no cover
    TestClient = None  # type: ignore[assignment]
    create_app = None  # type: ignore[assignment]


class ObservabilityTest(unittest.TestCase):
    def test_sanitize_for_log_masks_secrets_and_urls(self) -> None:
        self.assertEqual(sanitize_for_log("postgresql+psycopg://user:secret@localhost/db"), "postgresql+psycopg://user:***@localhost/db")
        self.assertEqual(sanitize_for_log("https://s3.local/bucket/object?X-Amz-Signature=abc&X-Amz-Credential=secret"), "https://s3.local/bucket/object?***")
        self.assertEqual(sanitize_for_log({"download_url": "https://s3.local/bucket/object?token=abc"})["download_url"], "https://s3.local/bucket/object?***")
        self.assertEqual(sanitize_for_log({"X-Amz-Signature": "abc"})["X-Amz-Signature"], "***")
        self.assertEqual(sanitize_for_log("token-abc-123"), "***")
        self.assertEqual(sanitize_for_log({"nested": "password-here"})["nested"], "***")

    def test_build_event_includes_core_fields(self) -> None:
        event = build_event("incident.created", organization_id="org-1", incident_id="inc-1", edge_worker_id="edge-1", user_id="user-1", detail="ok")
        self.assertEqual(event["action"], "incident.created")
        self.assertEqual(event["organization_id"], "org-1")
        self.assertEqual(event["incident_id"], "inc-1")
        self.assertEqual(event["edge_worker_id"], "edge-1")
        self.assertEqual(event["user_id"], "user-1")
        self.assertEqual(event["extra"]["detail"], "ok")

    def test_snapshot_metrics_serializes_tuple_keys(self) -> None:
        increment_metric("detections", ("accepted", "org-1"))
        self.assertGreaterEqual(snapshot_metrics()["detections"]["accepted|org-1"], 1)

    @unittest.skipIf(TestClient is None, "fastapi test client unavailable")
    def test_request_id_and_metrics_endpoint(self) -> None:
        if create_app is None:
            self.skipTest("fastapi app unavailable")
        app_factory = create_app
        container = build_container(repository_backend="memory", seed_dev=False)
        app = app_factory(container=container)  # type: ignore[operator]
        client = TestClient(app)
        response = client.get("/api/v1/health", headers={"X-Request-ID": "req-123"})
        self.assertEqual(response.headers.get("x-request-id"), "req-123")
        metrics = client.get("/api/v1/metrics")
        self.assertEqual(metrics.status_code, 200)
        self.assertIn("requests_total", metrics.json())

    @unittest.skipIf(TestClient is None, "fastapi test client unavailable")
    def test_metrics_requires_token_in_staging(self) -> None:
        if create_app is None:
            self.skipTest("fastapi app unavailable")
        from vigia_api.settings import Settings
        config = Settings(
            app_env="staging",
            cookie_secure=True,
            allowed_origins=["https://staging.vigia.local"],
            jwt_secret="super-strong-jwt-secret-1234567890",
            refresh_token_secret="super-strong-refresh-secret-1234567890",
            database_url="postgresql+psycopg://vigia:strong@db:5432/vigia",
            redis_url="redis://:strong@redis:6379/0",
            repository_backend="postgres",
            minio_access_key="minio-access-key-strong-12345",
            minio_secret_key="minio-secret-key-strong-12345",
            smtp_host="smtp.prod.local",
            smtp_user="smtp-user-strong-12345",
            smtp_password="smtp-pass-strong-12345",
            edge_worker_api_key="edge-api-key-strong-12345",
            edge_worker_client_id="edge-client-id-strong-12345",
            s3_endpoint_url="https://s3.staging.vigia.local",
            evidence_bucket_name="vigia-evidence-private",
            metrics_token="metrics-token-strong-12345",
        )
        app = create_app(config=config, container=build_container(config, seed_dev=False))  # type: ignore[arg-type]
        client = TestClient(app)
        self.assertEqual(client.get("/api/v1/metrics").status_code, 401)
        self.assertEqual(client.get("/api/v1/metrics", headers={"X-Metrics-Token": "metrics-token-strong-12345"}).status_code, 200)

    @unittest.skipIf(TestClient is None, "fastapi test client unavailable")
    def test_health_does_not_leak_secrets(self) -> None:
        if create_app is None:
            self.skipTest("fastapi app unavailable")
        app_factory = create_app
        container = build_container(repository_backend="memory", seed_dev=False)
        app = app_factory(container=container)  # type: ignore[operator]
        client = TestClient(app)
        response = client.get("/api/v1/health")
        self.assertNotIn(settings.jwt_secret, response.text)
        self.assertNotIn(settings.refresh_token_secret, response.text)


if __name__ == "__main__":
    unittest.main()
