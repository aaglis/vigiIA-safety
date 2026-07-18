import unittest
from datetime import datetime, timedelta, timezone
from typing import cast

from vigia_api.domain.edge_workers import EdgeWorkerStatus
from vigia_api.services.edge_workers import EdgeWorkerService

try:
    from sqlalchemy import create_engine  # type: ignore[import-not-found]
    from sqlalchemy.orm import sessionmaker  # type: ignore[import-not-found]
    from vigia_api.persistence.base import Base
    from vigia_api.persistence import models  # noqa: F401
    from vigia_api.persistence.repositories import SqlAlchemyEdgeWorkerRepository
    SQLALCHEMY_AVAILABLE = True
except Exception:
    SQLALCHEMY_AVAILABLE = False


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy not installed")
class EdgeWorkersPersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)  # type: ignore[possibly-unbound]
        Base.metadata.create_all(self.engine)  # type: ignore[possibly-unbound]
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)  # type: ignore[possibly-unbound]

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)  # type: ignore[possibly-unbound]

    def _service(self) -> EdgeWorkerService:
        service = EdgeWorkerService(repository=SqlAlchemyEdgeWorkerRepository(self.Session))  # type: ignore[possibly-unbound]
        service.camera_catalog = {}
        return service

    def test_register_auth_heartbeat_revoke_and_offline_persist(self) -> None:
        service = self._service()
        worker, api_key = service.register_worker("org-1", "site-1", "Worker", ["cam-1"])
        service.camera_catalog[("org-1", "site-1")] = {"cam-1"}

        reloaded = self._service()
        reloaded.camera_catalog[("org-1", "site-1")] = {"cam-1"}
        cfg = reloaded.config(worker.client_id, api_key)
        worker_payload = cast(dict[str, object], cfg["worker"])
        self.assertEqual(worker_payload["organization_id"], "org-1")

        telemetry = {"cv_mode": "real", "pending_queue": 2, "inactive_rules": ["ppe_violation:modelo-sem-classe-de-capacete"]}
        reloaded.heartbeat(worker.client_id, api_key, telemetry=telemetry)
        row = reloaded.repository.get(worker.id)
        self.assertIsNotNone(row.last_heartbeat_at)
        self.assertEqual(row.last_telemetry, telemetry)

        telemetry_reloaded = self._service()
        persisted_telemetry = telemetry_reloaded.repository.get(worker.id)
        self.assertIsNotNone(persisted_telemetry)
        self.assertEqual(persisted_telemetry.last_telemetry, telemetry)

        later = datetime.now(timezone.utc) + timedelta(seconds=3600)
        self.assertTrue(reloaded.is_offline(worker.id, threshold_seconds=60, now=later))

        reloaded.revoke(worker.id)
        revoked = self._service()
        persisted_worker = revoked.repository.get(worker.id)
        self.assertIsNotNone(persisted_worker)
        self.assertEqual(persisted_worker.status, EdgeWorkerStatus.REVOKED)
        with self.assertRaises(PermissionError):
            revoked.heartbeat(worker.client_id, api_key)

    def test_tenant_safe_detection_rejects_foreign_scope(self) -> None:
        service = self._service()
        worker, api_key = service.register_worker("org-1", "site-1", "Worker", ["cam-1"])
        service.camera_catalog[("org-1", "site-1")] = {"cam-1"}

        with self.assertRaises(PermissionError):
            service.submit_detection(worker.client_id, api_key, {"organization_id": "org-2", "site_id": "site-1", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "low"})
        with self.assertRaises(PermissionError):
            service.submit_detection(worker.client_id, api_key, {"site_id": "site-2", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "low"})
        with self.assertRaises(PermissionError):
            service.submit_detection(worker.client_id, api_key, {"camera_id": "cam-x", "zone_id": "zone-1", "severity": "low"})


if __name__ == "__main__":
    unittest.main()
