import unittest

from vigia_edge_worker.config import WorkerConfig
from vigia_edge_worker.detector import FrameInput
from vigia_edge_worker.real_detector import RealDetector, RealDetectorConfig


class _Box:
    def __init__(self, cls, conf, xyxy):
        self.cls = [cls]
        self.conf = [conf]
        self.xyxy = [xyxy]


class _Preds:
    def __init__(self, boxes):
        self.boxes = boxes


class _Model:
    def __init__(self, preds):
        self._preds = preds

    def __call__(self, image, verbose=False, conf=0.0):
        return [self._preds]


class _Img:
    shape = (360, 640, 3)

    def copy(self):
        return self


RESTRICTED = {"id": "z-rest", "site_id": "site-1", "zone_type": "restricted", "polygon_json": {"type": "polygon", "points": [[0.15, 0.4], [0.85, 0.4], [0.85, 0.95], [0.15, 0.95]]}}
PPE = {"id": "z-ppe", "site_id": "site-1", "zone_type": "ppe", "polygon_json": {}}


class RealDetectorYoloTest(unittest.TestCase):
    def _detector(self, preds):
        config = WorkerConfig(edge_worker_id="w", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="z-rest", cv_model_path="fake.pt")
        detector = RealDetector(config, RealDetectorConfig(enabled=True, model_version="ppe-yolo"))
        detector._model = _Model(preds)
        detector._class_categories = {0: "person", 1: "helmet"}
        detector._has_no_helmet_class = False
        detector.load_context({"zones": [RESTRICTED, PPE], "required_ppe": [{"item": "capacete"}]})
        return detector

    def _frame(self):
        return FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", frame=_Img(), width=640, height=360)

    def test_person_in_restricted_and_without_helmet_emits_both(self):
        detector = self._detector(_Preds([_Box(0, 0.9, [256, 108, 384, 306])]))
        results = detector.detect(self._frame())
        types = {r.event_type for r in results}
        self.assertIn("restricted_intrusion", types)
        self.assertIn("ppe_violation", types)
        self.assertEqual(results[0].event_type, "restricted_intrusion")
        self.assertEqual(results[0].model_version, "ppe-yolo")
        self.assertIn("bbox", results[0].evidence)
        self.assertEqual(results[0].metadata["cv_mode"], "real")

    def test_person_with_helmet_has_no_ppe_violation(self):
        detector = self._detector(_Preds([_Box(0, 0.9, [256, 108, 384, 324]), _Box(1, 0.8, [269, 100, 371, 144])]))
        types = {r.event_type for r in detector.detect(self._frame())}
        self.assertNotIn("ppe_violation", types)

    def test_disabled_detector_raises(self):
        config = WorkerConfig(edge_worker_id="w", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="z", cv_model_path="fake.pt")
        detector = RealDetector(config, RealDetectorConfig(enabled=False))
        from vigia_edge_worker.real_detector import RealDetectorError
        with self.assertRaises(RealDetectorError):
            detector.detect(self._frame())


if __name__ == "__main__":
    unittest.main()
