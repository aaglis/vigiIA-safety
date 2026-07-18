import unittest
from typing import cast

from vigia_api.container import build_container
from vigia_api.domain.operations import ZoneType


class EdgeWorkerConfigTest(unittest.TestCase):
    def test_config_includes_site_zones_rules_and_ppe(self) -> None:
        container = build_container(repository_backend="memory", seed_dev=False)
        repo = container.operations_repository
        site = repo.create_site("org-1", "HQ", site_id="site-1")
        raw_stream = "rtsp://camera-user:camera-pass@10.7.0.15:554/live"
        camera = repo.create_camera("org-1", site.id, "Cam 1", raw_stream, camera_id="cam-1")
        zone = repo.create_zone("org-1", site.id, camera.id, ZoneType.RESTRICTED, {"points": []}, zone_id="zone-1")
        rule = repo.create_safety_rule("org-1", "Helmet required", site_id=site.id, zone_id=zone.id, rule_id="rule-1")
        repo.create_required_ppe("org-1", rule.id, "helmet", site_id=site.id, zone_id=zone.id, ppe_id="ppe-1")
        worker, api_key = container.edge_worker_service.register_worker("org-1", site.id, "Worker", [camera.id])
        payload = cast(dict[str, object], container.edge_worker_service.config(worker.client_id, api_key))
        zones = cast(list[dict[str, object]], payload["zones"])
        rules = cast(list[dict[str, object]], payload["safety_rules"])
        ppes = cast(list[dict[str, object]], payload["required_ppe"])
        cameras = cast(list[dict[str, object]], payload["cameras"])
        self.assertEqual(payload["site_id"], site.id)
        self.assertEqual(payload["allowed_camera_ids"], [camera.id])
        self.assertEqual(cameras[0]["stream_identifier"], raw_stream)
        self.assertEqual(zones[0]["zone_type"], "restricted")
        self.assertEqual(rules[0]["name"], "Helmet required")
        self.assertEqual(ppes[0]["item"], "helmet")

    def test_config_does_not_leak_rules_or_ppe_from_another_site(self) -> None:
        container = build_container(repository_backend="memory", seed_dev=False)
        repo = container.operations_repository
        site = repo.create_site("org-1", "HQ", site_id="site-1")
        other_site = repo.create_site("org-1", "Warehouse", site_id="site-2")
        camera = repo.create_camera("org-1", site.id, "Cam 1", "stream-1", camera_id="cam-1")
        other_camera = repo.create_camera("org-1", other_site.id, "Cam 2", "stream-2", camera_id="cam-2")
        zone = repo.create_zone("org-1", site.id, camera.id, ZoneType.RESTRICTED, {"points": []}, zone_id="zone-1")
        repo.create_zone("org-1", other_site.id, other_camera.id, ZoneType.PPE, {"points": []}, zone_id="zone-2")
        current_rule = repo.create_safety_rule("org-1", "Current site", site_id=site.id, zone_id=zone.id, rule_id="rule-current")
        global_rule = repo.create_safety_rule("org-1", "Global org", rule_id="rule-global")
        leaked_rule = repo.create_safety_rule("org-1", "Other site", site_id=other_site.id, rule_id="rule-other")
        repo.create_required_ppe("org-1", current_rule.id, "helmet", site_id=site.id, zone_id=zone.id, ppe_id="ppe-current")
        repo.create_required_ppe("org-1", global_rule.id, "vest", ppe_id="ppe-global")
        repo.create_required_ppe("org-1", leaked_rule.id, "gloves", site_id=other_site.id, ppe_id="ppe-other")
        worker, api_key = container.edge_worker_service.register_worker("org-1", site.id, "Worker", [camera.id])

        payload = cast(dict[str, object], container.edge_worker_service.config(worker.client_id, api_key))

        rules = cast(list[dict[str, object]], payload["safety_rules"])
        ppes = cast(list[dict[str, object]], payload["required_ppe"])
        self.assertEqual({rule["id"] for rule in rules}, {"rule-current", "rule-global"})
        self.assertEqual({ppe["id"] for ppe in ppes}, {"ppe-current", "ppe-global"})


if __name__ == "__main__":
    unittest.main()
