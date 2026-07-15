import unittest
from typing import Any

from vigia_api.domain.incidents import IncidentStatus, parse_detection_event

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from vigia_api.persistence.base import Base
    from vigia_api.persistence import models  # noqa: F401
    from vigia_api.persistence.repositories import SqlAlchemyIncidentRepository
    SQLALCHEMY_AVAILABLE = True
except Exception:
    SQLALCHEMY_AVAILABLE = False


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy not installed")
class IncidentRepositoryPersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)

    def _repo(self) -> Any:
        return SqlAlchemyIncidentRepository(self.Session)

    def test_create_transition_audit_and_reload(self) -> None:
        repo = self._repo()
        incident = repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "high", "summary": "demo"}))
        self.assertEqual(incident.status, IncidentStatus.OPEN)

        reopened = self._repo()
        items = reopened.list_by_organization("org-1")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, incident.id)

        updated = reopened.transition("org-1", incident.id, IncidentStatus.ACKNOWLEDGED, "alice")
        updated = reopened.transition("org-1", incident.id, IncidentStatus.RESOLVED, "bob", reason="fixed")
        self.assertEqual(updated.status, IncidentStatus.RESOLVED)
        self.assertEqual(updated.resolved_by, "bob")
        self.assertEqual(updated.resolution_reason, "fixed")

        reload_again = self._repo()
        detailed = reload_again.get("org-1", incident.id)
        self.assertIsNotNone(detailed)
        self.assertEqual(detailed.status, IncidentStatus.RESOLVED)
        self.assertEqual(detailed.acknowledged_by, "alice")
        self.assertEqual(detailed.resolved_by, "bob")
        logs = reload_again.audit_logs("org-1", incident.id)
        self.assertEqual([entry.action for entry in logs], ["created", "incident.acknowledged", "incident.resolved"])
        self.assertEqual(logs[-1].metadata["reason"], "fixed")

    def test_tenant_scoping_blocks_foreign_incident(self) -> None:
        repo = self._repo()
        incident = repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "low"}))
        self.assertIsNone(repo.get("org-2", incident.id))
        self.assertEqual(repo.list_by_organization("org-2"), [])

    def test_create_from_detection_is_idempotent_by_org_and_event_id(self) -> None:
        repo = self._repo()
        payload = {"organization_id": "org-1", "event_id": "evt-1", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "high"}

        first = repo.create_from_detection(parse_detection_event(payload))
        second = repo.create_from_detection(parse_detection_event(payload))
        other_event = repo.create_from_detection(parse_detection_event({**payload, "event_id": "evt-2"}))
        other_org = repo.create_from_detection(parse_detection_event({**payload, "organization_id": "org-2"}))

        self.assertEqual(first.id, second.id)
        self.assertNotEqual(first.id, other_event.id)
        self.assertNotEqual(first.id, other_org.id)
        self.assertEqual(len(repo.list_by_organization("org-1")), 2)
        self.assertEqual(len(repo.audit_logs("org-1", first.id)), 1)


if __name__ == "__main__":
    unittest.main()
