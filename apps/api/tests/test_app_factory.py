import unittest

from vigia_api.container import build_container
from vigia_api.settings import Settings

try:
    from fastapi.testclient import TestClient  # type: ignore[import-not-found]

    from vigia_api.main import create_app
except Exception:  # pragma: no cover - optional FastAPI dependency on host
    TestClient = None  # type: ignore[assignment]
    create_app = None  # type: ignore[assignment]


class AppFactoryTest(unittest.TestCase):
    def test_memory_containers_do_not_share_state(self) -> None:
        first = build_container(repository_backend="memory", seed_dev=False)
        second = build_container(repository_backend="memory", seed_dev=False)

        worker, api_key = first.edge_worker_service.register_worker("org-1", "site-1", "worker", ["cam-1"])
        first.edge_worker_service.submit_detection(worker.client_id, api_key, {"camera_id": "cam-1", "zone_id": "zone-1", "severity": "high"})

        self.assertEqual(len(first.incident_repository.list_by_organization("org-1")), 1)
        self.assertEqual(len(second.incident_repository.list_by_organization("org-1")), 0)
        self.assertIs(first.auth_service.repository, first.invite_service.auth_repository)
        self.assertIs(first.auth_service.repository, first.account_recovery_service.auth_repository)

    def test_staging_and_production_reject_memory_backend(self) -> None:
        with self.assertRaises(ValueError):
            Settings(app_env="staging", repository_backend="memory")
        with self.assertRaises(ValueError):
            Settings(app_env="production", repository_backend="memory")

    @unittest.skipIf(TestClient is None, "fastapi test client unavailable")
    def test_create_app_attaches_explicit_container(self) -> None:
        container = build_container(repository_backend="memory", seed_dev=False)
        app = create_app(container=container)  # type: ignore[misc]

        self.assertIs(app.state.container, container)


if __name__ == "__main__":
    unittest.main()
