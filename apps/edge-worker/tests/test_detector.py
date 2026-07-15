import unittest

from vigia_edge_worker.config import WorkerConfig
from vigia_edge_worker.detector import FrameInput
from vigia_edge_worker.detector_factory import DetectorSelection, build_detector
from vigia_edge_worker.real_detector import RealDetector, RealDetectorConfig, RealDetectorError


class DetectorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = WorkerConfig(edge_worker_id="worker-1", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="zone-1")

    def test_mock_mode_is_deterministic(self) -> None:
        detector = build_detector(self.config, DetectorSelection(cv_mode="mock"))
        frame = FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z")
        result = detector.detect(frame)[0]
        self.assertEqual(result.event_type, "mock_detection")
        self.assertEqual(result.metadata["cv_mode"], "mock")

    def test_real_mode_requires_explicit_enablement(self) -> None:
        detector = build_detector(self.config, DetectorSelection(cv_mode="real"))
        self.assertIsInstance(detector, RealDetector)
        with self.assertRaises(RealDetectorError):
            detector.detect(FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", image_bytes=b"frame with marker"))

    def test_factory_uses_config_when_selection_is_omitted(self) -> None:
        config = WorkerConfig(edge_worker_id="worker-1", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="zone-1", cv_mode="real", cv_real_enabled=True, cv_real_marker="helmet", cv_real_model_version="real-cv-2")
        detector = build_detector(config)
        result = detector.detect(FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", image_bytes=b"helmet"))[0]
        self.assertEqual(result.model_version, "real-cv-2")

    def test_real_mode_emits_detection_only_when_marker_matches(self) -> None:
        detector = RealDetector(self.config, real_config=RealDetectorConfig(enabled=True, marker="helmet", model_version="real-cv-1"))
        no_hit = detector.detect(FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", image_bytes=b"plain frame"))
        hit = detector.detect(FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", image_bytes=b"plain helmet frame"))
        self.assertEqual(no_hit, [])
        self.assertEqual(hit[0].event_type, "real_detection")
        self.assertEqual(hit[0].metadata["cv_mode"], "real")


if __name__ == "__main__":
    unittest.main()
