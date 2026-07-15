import unittest

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from vigia_api.persistence.base import Base
    from vigia_api.persistence import models  # noqa: F401
    from vigia_api.scripts.seed_synthetic_incidents_postgres import run_baseline_postgres, seed_synthetic_incidents_postgres
    SQLALCHEMY_AVAILABLE = True
except Exception:
    SQLALCHEMY_AVAILABLE = False


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy not installed")
class SeedSyntheticIncidentsPostgresTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)

    def test_seed_and_measure_postgres_baseline(self) -> None:
        repo, evidence_service, incidents = seed_synthetic_incidents_postgres(self.Session, count=12)
        self.assertEqual(len(incidents), 12)
        self.assertGreaterEqual(len(repo.list_filtered("org-demo")), 12)
        self.assertGreaterEqual(len(evidence_service.list_evidence("org-demo", incident_id=incidents[0].id)), 1)

        result = run_baseline_postgres("sqlite+pysqlite:///:memory:", count=10)
        self.assertEqual(result["kind"], "incident_volume_baseline_postgres")
        self.assertEqual(result["count"], 10)
        self.assertTrue(result["postgres"])


if __name__ == "__main__":
    unittest.main()
