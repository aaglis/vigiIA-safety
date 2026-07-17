import unittest

from vigia_api.domain.auth import PlatformRole
from vigia_api.scripts.seed_demo import auth_repository, operations_repository, seed_demo


class SeedDemoTest(unittest.TestCase):
    def test_seed_demo_is_idempotent_and_creates_minimum_entities(self) -> None:
        first = seed_demo()
        second = seed_demo()

        self.assertEqual(first["user"]["platform_user_id"], "user-platform-admin")
        self.assertEqual(first["organization"]["id"], "org-demo")
        self.assertEqual(first["edge_worker"]["edge_worker_id"], "edge-worker-demo")
        self.assertFalse(first["incident"]["seeded"])
        self.assertEqual(first["counts"], second["counts"])
        self.assertGreaterEqual(first["counts"]["sites"], 3)
        self.assertGreaterEqual(first["counts"]["cameras"], 3)
        self.assertGreaterEqual(first["counts"]["zones"], 3)
        self.assertGreaterEqual(first["counts"]["workers"], 2)
        self.assertGreaterEqual(first["counts"]["edge_workers"], 1)
        self.assertGreaterEqual(first["counts"]["incidents"], 0)
        self.assertGreaterEqual(len(auth_repository.users), 1)
        org_admin = auth_repository.users_by_email["admin@vigia.local"]
        platform_admin = auth_repository.users_by_email["platform@vigia.local"]
        self.assertEqual(auth_repository.users[platform_admin].platform_role, PlatformRole.PLATFORM_ADMIN)
        self.assertEqual(auth_repository.users[org_admin].platform_role, PlatformRole.NONE)
        self.assertEqual(auth_repository.memberships[org_admin][0].role, "org_owner")
        self.assertEqual(auth_repository.memberships[platform_admin][0].role, "platform_admin")
        self.assertEqual(auth_repository.memberships[org_admin][0].organization.id, "org-demo")
        self.assertIn("site-demo", operations_repository.sites)
        self.assertIn("camera-demo-01", operations_repository.cameras)
        self.assertIn("zone-demo-01", operations_repository.zones)
        self.assertIn("worker-demo-01", operations_repository.workers)
        self.assertIn("site-demo-patio-sul", operations_repository.sites)
        self.assertIn("site-demo-doca-norte", operations_repository.sites)
        self.assertIn("camera-demo-patio-sul-01", operations_repository.cameras)
        self.assertIn("camera-demo-doca-norte-01", operations_repository.cameras)
        self.assertIn("zone-demo-patio-sul-access", operations_repository.zones)
        self.assertIn("zone-demo-doca-norte-ppe", operations_repository.zones)
        self.assertIn("rule-helmet-required-1", operations_repository.safety_rules)
        self.assertIn("rule-reflective-vest-patio-sul", operations_repository.safety_rules)
        self.assertIn("rule-goggles-gloves-doca-norte", operations_repository.safety_rules)
        self.assertIn("rule-restricted-access-maintenance", operations_repository.safety_rules)
        self.assertIn("ppe-helmet-demo", operations_repository.required_ppe)
        self.assertIn("ppe-vest-patio-sul", operations_repository.required_ppe)
        self.assertIn("ppe-goggles-doca-norte", operations_repository.required_ppe)
        self.assertIn("ppe-gloves-doca-norte", operations_repository.required_ppe)
        for ppe in operations_repository.required_ppe.values():
            self.assertLessEqual(len(ppe.id), 36)

        camera = operations_repository.cameras["camera-demo-patio-sul-01"]
        self.assertEqual(camera.metadata["location_label"], "Pátio Sul / Portaria 2")
        self.assertIn("missing_reflective_vest", camera.metadata["cv_scenarios"])
        self.assertIn("video_fixture_url", camera.metadata)

    def test_seed_demo_with_incident_opt_in_creates_acknowledged_incident(self) -> None:
        result = seed_demo(with_incident=True)
        self.assertTrue(result["incident"]["seeded"])
        self.assertEqual(result["incident"]["status"], "acknowledged")


if __name__ == "__main__":
    unittest.main()
