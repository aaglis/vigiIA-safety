import unittest

from vigia_api.scripts.seed_synthetic_incidents import run_baseline, seed_synthetic_incidents


class SyntheticIncidentBaselineTest(unittest.TestCase):
    def test_seed_is_synthetic_and_filterable(self) -> None:
        repo, evidence_service, incidents = seed_synthetic_incidents(count=120, organization_id="org-test", days=10)
        self.assertEqual(len(incidents), 120)
        self.assertEqual(len(repo.list_filtered("org-test", status="open")), 30)
        self.assertEqual(len(repo.list_filtered("org-test", severity="high")), 30)
        self.assertGreater(len(repo.list_filtered("org-test", site_id="site-demo")), 0)
        self.assertGreater(len(evidence_service.list_evidence("org-test")), 0)
        self.assertEqual(len(repo.list_by_organization("org-other")), 0)

    def test_baseline_reports_dashboard_queries(self) -> None:
        report = run_baseline(count=120, organization_id="org-test", days=10)
        labels = {item["label"] for item in report["measurements"]}
        self.assertEqual(report["count"], 120)
        self.assertTrue(report["synthetic_only"])
        self.assertIn("list_first_page", labels)
        self.assertIn("filter_site_camera_zone", labels)
        self.assertIn("detail_lookup", labels)
        self.assertIn("evidence_lookup", labels)
        for item in report["measurements"]:
            self.assertGreaterEqual(item["elapsed_ms"], 0)


if __name__ == "__main__":
    unittest.main()
