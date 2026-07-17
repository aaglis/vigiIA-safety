import unittest

from vigia_edge_worker.cv_analysis import DetectedBox, evaluate_violations

RESTRICTED_ZONE = {"id": "z-rest", "zone_type": "restricted", "polygon_json": {"points": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.9], [0.2, 0.9]]}}
PPE_ZONE = {"id": "z-ppe", "zone_type": "ppe", "polygon_json": {}}
HELMET_PPE = [{"item": "capacete"}]


class RestrictedIntrusionTest(unittest.TestCase):
    def test_person_inside_restricted_zone_triggers_intrusion(self) -> None:
        person = DetectedBox("person", 0.9, (0.4, 0.3, 0.6, 0.85))
        violations = evaluate_violations([person], [RESTRICTED_ZONE], [], head_class_available=False)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].event_type, "restricted_intrusion")
        self.assertEqual(violations[0].zone_id, "z-rest")

    def test_person_outside_zone_is_ignored(self) -> None:
        person = DetectedBox("person", 0.9, (0.0, 0.0, 0.1, 0.1))
        self.assertEqual(evaluate_violations([person], [RESTRICTED_ZONE], [], head_class_available=False), [])


class PpeHelmetTest(unittest.TestCase):
    def test_person_without_helmet_triggers_ppe_violation(self) -> None:
        person = DetectedBox("person", 0.88, (0.4, 0.3, 0.6, 0.9))
        violations = evaluate_violations([person], [PPE_ZONE], HELMET_PPE, head_class_available=False)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].event_type, "ppe_violation")
        self.assertEqual(violations[0].metadata["ppe_item"], "capacete")

    def test_person_with_helmet_is_compliant(self) -> None:
        person = DetectedBox("person", 0.88, (0.4, 0.3, 0.6, 0.9))
        helmet = DetectedBox("helmet", 0.8, (0.42, 0.28, 0.58, 0.4))
        self.assertEqual(evaluate_violations([person, helmet], [PPE_ZONE], HELMET_PPE, head_class_available=False), [])

    def test_direct_no_helmet_class(self) -> None:
        head = DetectedBox("no_helmet", 0.77, (0.45, 0.25, 0.55, 0.4))
        violations = evaluate_violations([head], [PPE_ZONE], HELMET_PPE, head_class_available=True)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].event_type, "ppe_violation")
        self.assertEqual(violations[0].category, "no_helmet")

    def test_direct_no_helmet_class_respects_zone_polygon(self) -> None:
        # Zona de EPI COM polígono: exercita o caminho de geometria no modo head_class_available.
        ppe_polygon = {"id": "z-ppe-poly", "zone_type": "ppe", "polygon_json": {"points": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.9], [0.2, 0.9]]}}
        inside = DetectedBox("no_helmet", 0.9, (0.45, 0.5, 0.55, 0.7))
        outside = DetectedBox("no_helmet", 0.9, (0.01, 0.01, 0.05, 0.05))
        violations = evaluate_violations([inside, outside], [ppe_polygon], HELMET_PPE, head_class_available=True)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].bbox, inside.bbox)


if __name__ == "__main__":
    unittest.main()
