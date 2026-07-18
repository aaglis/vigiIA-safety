import unittest

from vigia_edge_worker.detector import DetectionResult, FrameInput
from vigia_edge_worker.rules import RuleEngine


class RulesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = RuleEngine(cooldown_seconds=10)
        self.engine.load_context({
            "site_id": "site-1",
            "allowed_camera_ids": ["cam-1"],
            "zones": [
                {"id": "zone-critical", "zone_type": "restricted"},
                {"id": "zone-info", "zone_type": "access"},
            ],
        })

    def test_critical_and_info_zones_map_to_severity(self) -> None:
        frame = FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z")
        critical = self.engine.apply(frame, DetectionResult(event_type="real_detection", confidence=0.9, model_version="real-cv-1", zone_id="zone-critical"))
        info = self.engine.apply(frame, DetectionResult(event_type="real_detection", confidence=0.9, model_version="real-cv-1", zone_id="zone-info"))
        assert critical is not None and info is not None
        self.assertEqual(critical.severity, "high")
        self.assertIn("Restricted", critical.summary)
        self.assertEqual(info.severity, "low")
        self.assertIn("Informational", info.summary)

    def test_cooldown_suppresses_repeated_camera_zone_event(self) -> None:
        frame = FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z")
        first = self.engine.apply(frame, DetectionResult(event_type="real_detection", confidence=0.9, model_version="real-cv-1", zone_id="zone-critical"))
        later_frame = FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:01Z")
        second = self.engine.apply(later_frame, DetectionResult(event_type="real_detection", confidence=0.9, model_version="real-cv-1", zone_id="zone-critical"))
        self.assertIsNotNone(first)
        self.assertIsNone(second)


if __name__ == "__main__":
    unittest.main()
