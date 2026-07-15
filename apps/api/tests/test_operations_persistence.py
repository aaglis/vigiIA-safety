import unittest

from vigia_api.domain.operations import EntityStatus, ZoneType

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from vigia_api.persistence.base import Base
    from vigia_api.persistence import models  # noqa: F401
    from vigia_api.persistence.operations_repository import SqlAlchemyOperationsRepository
    SQLALCHEMY_AVAILABLE = True
except Exception:
    SQLALCHEMY_AVAILABLE = False


@unittest.skipUnless(SQLALCHEMY_AVAILABLE, "SQLAlchemy not installed")
class OperationsPersistenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        self.repo = SqlAlchemyOperationsRepository(self.Session)

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)

    def test_create_and_reload_catalog_entities(self) -> None:
        site = self.repo.create_site("org-1", "HQ", "Main street", site_id="site-demo")
        camera = self.repo.create_camera("org-1", site.id, "Gate", "stream-1", metadata={"rtsp": "rtsp://camera"}, camera_id="camera-demo-01")
        zone = self.repo.create_zone("org-1", site.id, camera.id, ZoneType.ACCESS, {"points": [[0, 0], [1, 1]]}, zone_id="zone-demo-01")
        worker = self.repo.create_worker("org-1", "Alice", "INT-001", site_id=site.id, worker_id="worker-demo-01")
        rule = self.repo.create_safety_rule("org-1", "Helmet required", site_id=site.id, zone_id=zone.id, rule_id="rule-helmet-required-1")
        ppe = self.repo.create_required_ppe("org-1", rule.id, "helmet", site_id=site.id, zone_id=zone.id, ppe_id="ppe-helmet-1")

        reloaded = SqlAlchemyOperationsRepository(self.Session)
        self.assertEqual(reloaded.list_sites("org-1")[0].id, "site-demo")
        self.assertEqual(reloaded.list_cameras("org-1")[0].id, "camera-demo-01")
        self.assertEqual(reloaded.list_zones("org-1")[0].id, "zone-demo-01")
        self.assertEqual(reloaded.list_workers("org-1")[0].id, "worker-demo-01")
        self.assertEqual(reloaded.list_safety_rules("org-1")[0].id, "rule-helmet-required-1")
        self.assertEqual(reloaded.list_required_ppe("org-1")[0].id, "ppe-helmet-1")

    def test_cross_tenant_relationships_are_blocked(self) -> None:
        site = self.repo.create_site("org-1", "HQ", site_id="site-demo")
        other_site = self.repo.create_site("org-2", "Other", site_id="site-other")
        camera = self.repo.create_camera("org-1", site.id, "Cam", "stream-1", camera_id="camera-1")
        zone = self.repo.create_zone("org-1", site.id, camera.id, ZoneType.ACCESS, {}, zone_id="zone-1")
        rule = self.repo.create_safety_rule("org-1", "Rule", site_id=site.id, zone_id=zone.id, rule_id="rule-1")
        with self.assertRaises(KeyError):
            self.repo.create_camera("org-2", site.id, "Bad", "stream-x")
        with self.assertRaises(KeyError):
            self.repo.create_zone("org-2", other_site.id, camera.id, ZoneType.RESTRICTED, {})
        with self.assertRaises(KeyError):
            self.repo.create_safety_rule("org-2", "Bad", zone_id=zone.id)
        with self.assertRaises(KeyError):
            self.repo.create_required_ppe("org-2", rule.id, "gloves")


if __name__ == "__main__":
    unittest.main()
