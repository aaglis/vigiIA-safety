import unittest
from typing import Any, cast

from vigia_api.domain.evidence import EvidenceKind, EvidenceSource
from vigia_api.services.evidence import EvidenceService

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from vigia_api.persistence.base import Base
    from vigia_api.persistence import models  # noqa: F401
    from vigia_api.persistence.repositories import SqlAlchemyEvidenceRepository
    SQLALCHEMY_AVAILABLE = True
except Exception:
    SQLALCHEMY_AVAILABLE = False


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy not installed")
class EvidenceRepositoryPersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)

    def _service(self) -> EvidenceService:
        return EvidenceService(metadata_repository=cast(Any, SqlAlchemyEvidenceRepository(self.Session)))

    def test_register_download_purge_and_reload(self) -> None:
        service = self._service()
        evidence = service.register_evidence("org-1", "inc-1", "file-1", "image/jpeg", 123, "user-1", EvidenceSource.USER, EvidenceKind.SNAPSHOT, {"x": 1})
        self.assertEqual(evidence.object_key, "org/org-1/incidents/inc-1/evidence/file-1")

        reloaded = self._service()
        found = reloaded._find_evidence("org-1", "inc-1", "file-1")
        self.assertEqual(found.uploaded_by, "user-1")
        self.assertEqual(found.metadata["x"], 1)

        reloaded.set_retention_policy("org-1", snapshot_days=0)
        preview = reloaded.preview_expired_evidence("org-1")
        self.assertEqual(len(preview), 1)
        result = reloaded.purge_expired_evidence("org-1", confirm=True, actor_user_id="actor-1")
        self.assertEqual(result["count"], 1)

        again = self._service()
        with self.assertRaises(KeyError):
            again.get_download_url("org-1", "inc-1", "file-1", "actor-1")
        record = cast(Any, again.metadata_repository).get("org-1", "inc-1", "file-1")
        self.assertIsNotNone(record)
        self.assertIsNotNone(record.deleted_at)
        self.assertEqual(cast(Any, again.metadata_repository).audit_logs("org-1", "inc-1")[-1].action, "purge.confirm")

    def test_cross_tenant_access_is_blocked(self) -> None:
        service = self._service()
        service.register_evidence("org-1", "inc-1", "file-1", "image/jpeg", 123, "user-1", EvidenceSource.USER)
        with self.assertRaises(KeyError):
            service.get_download_url("org-2", "inc-1", "file-1", "actor-1")


if __name__ == "__main__":
    unittest.main()
