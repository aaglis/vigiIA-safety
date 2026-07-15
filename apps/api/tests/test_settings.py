import os
import unittest

from vigia_api.settings import Settings


class SettingsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._env = os.environ.copy()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env)

    def test_production_without_jwt_secret_fails(self) -> None:
        os.environ["APP_ENV"] = "production"
        with self.assertRaises(ValueError):
            Settings(jwt_secret="dev-only-jwt-secret-change-me", refresh_token_secret="dev-only-refresh-secret-change-me")

    def test_production_with_weak_secrets_fails(self) -> None:
        os.environ["APP_ENV"] = "production"
        with self.assertRaises(ValueError):
            Settings(
                jwt_secret="change-me",
                refresh_token_secret="example",
                database_url="postgresql+psycopg://user:pass@db:5432/vigia",
                redis_url="redis://redis:6379/0",
                minio_access_key="vigia",
                minio_secret_key="password",
                smtp_host="smtp.example.com",
                smtp_user="user",
                smtp_password="password",
                edge_worker_api_key="dev-only",
                edge_worker_client_id="edge-1",
            )

    def test_production_with_strong_secrets_passes(self) -> None:
        os.environ["APP_ENV"] = "production"
        settings = Settings(
            jwt_secret="super-strong-jwt-secret-1234567890",
            refresh_token_secret="super-strong-refresh-secret-1234567890",
            database_url="postgresql+psycopg://vigia:strong@db:5432/vigia",
            redis_url="redis://:strong@redis:6379/0",
            repository_backend="postgres",
            cookie_secure=True,
            allowed_origins=["https://staging.vigia.local"],
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
        self.assertEqual(settings.app_env, "production")

    def test_staging_rejects_demo_credentials(self) -> None:
        os.environ["APP_ENV"] = "staging"
        with self.assertRaises(ValueError):
            Settings(
                jwt_secret="super-strong-jwt-secret-1234567890",
                refresh_token_secret="super-strong-refresh-secret-1234567890",
                database_url="postgresql+psycopg://vigia:strong@db:5432/vigia",
                redis_url="redis://:strong@redis:6379/0",
                repository_backend="postgres",
                minio_access_key="minio-access-key-strong-12345",
                minio_secret_key="minio-secret-key-strong-12345",
                smtp_host="smtp.prod.local",
                smtp_user="dev-only",
                smtp_password="smtp-pass-strong-12345",
                edge_worker_api_key="edge-api-key-strong-12345",
                edge_worker_client_id="edge-client-id-strong-12345",
                smtp_from="alerts@vigia.local",
            )

    def test_staging_rejects_insecure_or_placeholder_storage_and_origins(self) -> None:
        os.environ["APP_ENV"] = "staging"
        with self.assertRaises(ValueError):
            Settings(
                jwt_secret="super-strong-jwt-secret-1234567890",
                refresh_token_secret="super-strong-refresh-secret-1234567890",
                database_url="postgresql+psycopg://vigia:strong@db:5432/vigia",
                redis_url="redis://:strong@redis:6379/0",
                repository_backend="postgres",
                cookie_secure=False,
                allowed_origins=["http://localhost:3000"],
                minio_access_key="minio-access-key-strong-12345",
                minio_secret_key="minio-secret-key-strong-12345",
                smtp_host="smtp.prod.local",
                smtp_user="smtp-user-strong-12345",
                smtp_password="smtp-pass-strong-12345",
                edge_worker_api_key="edge-api-key-strong-12345",
                edge_worker_client_id="edge-client-id-strong-12345",
                s3_endpoint_url="http://minio.local:9000",
                evidence_bucket_name="vigia-evidence-private",
            )

    def test_staging_requires_metrics_token(self) -> None:
        os.environ["APP_ENV"] = "staging"
        with self.assertRaises(ValueError):
            Settings(
                jwt_secret="super-strong-jwt-secret-1234567890",
                refresh_token_secret="super-strong-refresh-secret-1234567890",
                database_url="postgresql+psycopg://vigia:strong@db:5432/vigia",
                redis_url="redis://:strong@redis:6379/0",
                repository_backend="postgres",
                cookie_secure=True,
                allowed_origins=["https://staging.vigia.local"],
                minio_access_key="minio-access-key-strong-12345",
                minio_secret_key="minio-secret-key-strong-12345",
                smtp_host="smtp.prod.local",
                smtp_user="smtp-user-strong-12345",
                smtp_password="smtp-pass-strong-12345",
                edge_worker_api_key="edge-api-key-strong-12345",
                edge_worker_client_id="edge-client-id-strong-12345",
                s3_endpoint_url="https://s3.staging.vigia.local",
                evidence_bucket_name="vigia-evidence-private",
                metrics_token="dev-only",
            )

    def test_dev_allows_placeholders(self) -> None:
        os.environ["APP_ENV"] = "dev"
        settings = Settings()
        self.assertEqual(settings.jwt_secret, "dev-only-jwt-secret-change-me")
        self.assertEqual(settings.refresh_token_secret, "dev-only-refresh-secret-change-me")


if __name__ == "__main__":
    unittest.main()
