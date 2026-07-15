import unittest

from vigia_api.domain.operations import EntityStatus, ZoneType
from vigia_api.services.operations import InMemoryOperationsRepository


class OperationsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = InMemoryOperationsRepository()
        self.site = self.repo.create_site("org-1", "HQ", "Main street")
        self.department = self.repo.create_department("org-1", self.site.id, "Security")
        self.worker = self.repo.create_worker("org-1", "Alice", "INT-001", site_id=self.site.id, department_id=self.department.id, contact="alice@acme.local")
        self.camera = self.repo.create_camera("org-1", self.site.id, "Gate", "stream-1", metadata={"rtsp": "rtsp://camera"})
        self.zone = self.repo.create_zone("org-1", self.site.id, self.camera.id, ZoneType.ACCESS, {"points": [[0, 0], [1, 1]]})
        self.rule = self.repo.create_safety_rule("org-1", "Helmet required", site_id=self.site.id, zone_id=self.zone.id)
        self.ppe = self.repo.create_required_ppe("org-1", self.rule.id, "helmet", site_id=self.site.id, zone_id=self.zone.id)

    def test_create_entities_same_org(self) -> None:
        self.assertEqual(self.site.organization_id, "org-1")
        self.assertEqual(self.department.site_id, self.site.id)
        self.assertEqual(self.worker.department_id, self.department.id)
        self.assertEqual(self.camera.site_id, self.site.id)
        self.assertEqual(self.zone.camera_id, self.camera.id)
        self.assertEqual(self.rule.zone_id, self.zone.id)
        self.assertEqual(self.ppe.rule_id, self.rule.id)

    def test_cross_tenant_relationships_are_blocked(self) -> None:
        other_site = self.repo.create_site("org-2", "Remote")
        other_camera = self.repo.create_camera("org-2", other_site.id, "Cam", "stream-x")
        other_rule = self.repo.create_safety_rule("org-2", "Rule B")
        with self.assertRaises(KeyError):
            self.repo.create_department("org-1", other_site.id, "Bad Dept")
        with self.assertRaises(KeyError):
            self.repo.create_camera("org-1", other_site.id, "Bad Cam", "stream-bad")
        with self.assertRaises(KeyError):
            self.repo.create_zone("org-1", self.site.id, other_camera.id, ZoneType.RESTRICTED, {})
        other_zone = self.repo.create_zone("org-2", other_site.id, other_camera.id, ZoneType.ACCESS, {})
        with self.assertRaises(KeyError):
            self.repo.create_safety_rule("org-1", "Bad Rule", zone_id=other_zone.id)
        with self.assertRaises(KeyError):
            self.repo.create_required_ppe("org-1", other_rule.id, "gloves")

    def test_worker_optional_scope_and_validation(self) -> None:
        standalone = self.repo.create_worker("org-1", "Bob", "INT-002")
        self.assertIsNone(standalone.site_id)
        other_site = self.repo.create_site("org-1", "Branch")
        other_dept = self.repo.create_department("org-1", other_site.id, "Ops")
        with self.assertRaises(ValueError):
            self.repo.create_worker("org-1", "Mallory", "INT-003", site_id=self.site.id, department_id=other_dept.id)

    def test_audit_log_preserves_optional_org(self) -> None:
        self.repo._record(None, "system", "bootstrap", "system", "boot-1", ip="127.0.0.1", note="done")
        log = self.repo.audit_logs[-1]
        self.assertIsNone(log.organization_id)
        self.assertEqual(log.ip, "127.0.0.1")
        self.assertEqual(log.metadata_json["note"], "done")

    def test_scope_helpers(self) -> None:
        self.assertEqual(self.repo.ensure_camera_scope("org-1", self.site.id, self.camera.id).id, self.camera.id)
        self.assertEqual(self.repo.ensure_worker_scope("org-1", self.site.id, self.worker.id).id, self.worker.id)
        with self.assertRaises(KeyError):
            self.repo.ensure_camera_scope("org-2", self.site.id, self.camera.id)
        with self.assertRaises(KeyError):
            self.repo.ensure_worker_scope("org-2", self.site.id, self.worker.id)


if __name__ == "__main__":
    unittest.main()
