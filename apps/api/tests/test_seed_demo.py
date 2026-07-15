import unittest

from vigia_api.scripts.seed_demo import auth_repository, operations_repository, seed_demo


class SeedDemoTest(unittest.TestCase):
    def test_seed_demo_is_idempotent_and_creates_minimum_entities(self) -> None:
        first = seed_demo()
        second = seed_demo()

        self.assertEqual(first["user"]["user_id"], "user-dev")
        self.assertEqual(first["organization"]["id"], "org-demo")
        self.assertEqual(first["edge_worker"]["edge_worker_id"], "edge-worker-demo")
        self.assertEqual(first["incident"]["status"], "acknowledged")
        self.assertEqual(first["counts"], second["counts"])
        self.assertEqual(first["counts"]["sites"], 1)
        self.assertEqual(first["counts"]["cameras"], 1)
        self.assertEqual(first["counts"]["zones"], 1)
        self.assertEqual(first["counts"]["workers"], 1)
        self.assertGreaterEqual(len(auth_repository.users), 1)
        membership = auth_repository.memberships[first["user"]["user_id"]][0]
        self.assertEqual(membership.role, "org_owner")
        self.assertEqual(membership.organization.id, "org-demo")
        self.assertIn("site-demo", operations_repository.sites)
        self.assertIn("camera-demo-01", operations_repository.cameras)
        self.assertIn("zone-demo-01", operations_repository.zones)
        self.assertIn("worker-demo-01", operations_repository.workers)


if __name__ == "__main__":
    unittest.main()
