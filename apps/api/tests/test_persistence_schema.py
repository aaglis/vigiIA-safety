import unittest

from vigia_api.domain.edge_workers import EdgeWorker, EdgeWorkerStatus
from vigia_api.domain.incidents import Incident, IncidentStatus

try:
    from sqlalchemy import create_engine, inspect
    from sqlalchemy.orm import sessionmaker
    from vigia_api.persistence.base import Base
    from vigia_api.persistence import models  # noqa: F401
    from vigia_api.persistence.repositories import SqlAlchemyEdgeWorkerRepository, SqlAlchemyIncidentRepository
    SQLALCHEMY_AVAILABLE = True
except Exception:
    SQLALCHEMY_AVAILABLE = False


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy not installed")
class PersistenceSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)

    def test_schema_constraints(self) -> None:
        inspector = inspect(self.engine)
        users = inspector.get_unique_constraints("users")
        memberships = inspector.get_unique_constraints("organization_memberships")
        incidents = inspector.get_unique_constraints("incidents")
        self.assertTrue(any(c["name"] == "uq_users_email_normalized" for c in users))
        self.assertTrue(any(c["name"] == "uq_memberships_org_user" for c in memberships))
        self.assertTrue(any(c["name"] == "uq_incidents_org_detection_event" for c in incidents))

    def test_incident_and_worker_persist_across_repositories(self) -> None:
        incident_repo = SqlAlchemyIncidentRepository(self.Session)
        worker_repo = SqlAlchemyEdgeWorkerRepository(self.Session)

        incident = Incident(
            id="inc-1",
            organization_id="org-1",
            site_id="site-1",
            detection_event_id="evt-1",
            camera_id="cam-1",
            zone_id="zone-1",
            worker_id="worker-1",
            event_type="detection",
            severity="high",
            summary="test incident",
            confidence=0.9,
            metadata={"source": "test"},
            status=IncidentStatus.OPEN,
        )
        worker = EdgeWorker(
            id="worker-1",
            organization_id="org-1",
            site_id="site-1",
            name="Worker",
            client_id="client-1",
            api_key_hash="hash",
            allowed_camera_ids=["cam-1"],
            status=EdgeWorkerStatus.ACTIVE,
        )

        incident_repo.save(incident)
        worker_repo.save(worker)

        # simulate new app/process
        incident_repo_2 = SqlAlchemyIncidentRepository(self.Session)
        worker_repo_2 = SqlAlchemyEdgeWorkerRepository(self.Session)

        incident_row = incident_repo_2.get("org-1", "inc-1")
        worker_row = worker_repo_2.get("worker-1")
        self.assertIsNotNone(incident_row)
        self.assertIsNotNone(worker_row)
        self.assertEqual(incident_row.organization_id, "org-1")
        self.assertEqual(worker_row.organization_id, "org-1")
        self.assertEqual(worker_row.allowed_camera_ids, ["cam-1"])


if __name__ == "__main__":
    unittest.main()
