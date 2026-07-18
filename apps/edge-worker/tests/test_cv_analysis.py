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

    def test_person_with_clipped_feet_is_not_counted_inside_zone(self) -> None:
        clipped_person = DetectedBox("person", 0.9, (0.4, 0.3, 0.6, 1.0))
        self.assertEqual(evaluate_violations([clipped_person], [RESTRICTED_ZONE], [], head_class_available=False), [])

    def test_person_with_top_clipped_but_visible_feet_still_uses_floor_point(self) -> None:
        top_clipped_person = DetectedBox("person", 0.9, (0.4, -0.1, 0.6, 0.85))
        violations = evaluate_violations([top_clipped_person], [RESTRICTED_ZONE], [], head_class_available=False)
        self.assertEqual([v.event_type for v in violations], ["restricted_intrusion"])


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
        person = DetectedBox("person", 0.88, (0.4, 0.3, 0.6, 0.9))
        head = DetectedBox("no_helmet", 0.77, (0.45, 0.25, 0.55, 0.4))
        violations = evaluate_violations([person, head], [PPE_ZONE], HELMET_PPE, head_class_available=True)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].event_type, "ppe_violation")
        self.assertEqual(violations[0].category, "no_helmet")
        self.assertEqual(violations[0].bbox, person.bbox)
        self.assertEqual(violations[0].metadata["head_bbox"], head.bbox)

    def test_direct_no_helmet_class_without_person_does_not_infer_zone(self) -> None:
        head = DetectedBox("no_helmet", 0.77, (0.45, 0.25, 0.55, 0.4))
        self.assertEqual(evaluate_violations([head], [PPE_ZONE], HELMET_PPE, head_class_available=True), [])

    def test_direct_no_helmet_class_respects_zone_polygon(self) -> None:
        # Zona de EPI COM polígono: exercita o caminho de geometria no modo head_class_available.
        ppe_polygon = {"id": "z-ppe-poly", "zone_type": "ppe", "polygon_json": {"points": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.9], [0.2, 0.9]]}}
        inside_person = DetectedBox("person", 0.9, (0.4, 0.2, 0.6, 0.85))
        inside_head = DetectedBox("no_helmet", 0.9, (0.45, 0.18, 0.55, 0.35))
        outside_person = DetectedBox("person", 0.9, (0.01, 0.01, 0.1, 0.1))
        outside_head = DetectedBox("no_helmet", 0.9, (0.03, 0.0, 0.08, 0.04))
        violations = evaluate_violations([inside_person, inside_head, outside_person, outside_head], [ppe_polygon], HELMET_PPE, head_class_available=True)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].bbox, inside_person.bbox)

    def test_clipped_feet_do_not_trigger_ppe_zone_membership(self) -> None:
        ppe_polygon = {"id": "z-ppe-poly", "zone_type": "ppe", "polygon_json": {"points": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.9], [0.2, 0.9]]}}
        clipped_person = DetectedBox("person", 0.9, (0.4, 0.2, 0.6, 1.0))
        head = DetectedBox("no_helmet", 0.9, (0.45, 0.18, 0.55, 0.35))
        violations = evaluate_violations([clipped_person, head], [ppe_polygon], HELMET_PPE, head_class_available=True)
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()


class PpeWithoutHelmetClassTest(unittest.TestCase):
    """Modelo que não enxerga capacete não pode acusar ausência de capacete.

    Com o COCO (yolov8n), a lista de capacetes vem sempre vazia — o ramo person+helmet
    concluía "ninguém está de capacete" e acusava 100% das pessoas na zona de EPI.
    """

    def setUp(self):
        self.pessoa = DetectedBox(category="person", confidence=0.9, bbox=(0.4, 0.3, 0.6, 0.9))
        self.zona_ppe = {"id": "z-ppe", "zone_type": "ppe", "polygon_json": {}}

    def test_modelo_sem_classe_de_capacete_nao_acusa_epi(self):
        violacoes = evaluate_violations([self.pessoa], [self.zona_ppe], [], head_class_available=False, can_see_helmet=False)
        self.assertEqual(violacoes, [], "acusou EPI com modelo que não vê capacete")

    def test_modelo_com_capacete_continua_detectando_ausencia(self):
        violacoes = evaluate_violations([self.pessoa], [self.zona_ppe], [], head_class_available=False, can_see_helmet=True)
        self.assertEqual([v.event_type for v in violacoes], ["ppe_violation"])

    def test_pessoa_usando_capacete_nao_vira_violacao(self):
        capacete = DetectedBox(category="helmet", confidence=0.8, bbox=(0.45, 0.31, 0.55, 0.4))
        violacoes = evaluate_violations([self.pessoa, capacete], [self.zona_ppe], [], head_class_available=False, can_see_helmet=True)
        self.assertEqual(violacoes, [])

    def test_intrusao_continua_funcionando_sem_classe_de_capacete(self):
        zona_restrita = {"id": "z-rest", "zone_type": "restricted", "polygon_json": {}}
        violacoes = evaluate_violations([self.pessoa], [zona_restrita], [], head_class_available=False, can_see_helmet=False)
        self.assertEqual([v.event_type for v in violacoes], ["restricted_intrusion"])
