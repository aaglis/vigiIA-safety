import unittest

from vigia_edge_worker.geometry import bbox_base_center, bbox_base_center_visible, normalize_bbox, parse_polygon, point_in_polygon


class GeometryTest(unittest.TestCase):
    def test_parse_polygon_variants(self) -> None:
        self.assertEqual(parse_polygon({"points": [[0, 0], [1, 0], [1, 1]]}), [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)])
        polygon = parse_polygon({"points": [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 1, "y": 1}]})
        self.assertIsNotNone(polygon)
        assert polygon is not None
        self.assertEqual(polygon[0], (0.0, 0.0))
        self.assertIsNone(parse_polygon({}))
        self.assertIsNone(parse_polygon({"points": [[0, 0]]}))
        self.assertIsNone(parse_polygon(None))

    def test_point_in_polygon(self) -> None:
        square = [(0.2, 0.2), (0.8, 0.2), (0.8, 0.9), (0.2, 0.9)]
        self.assertTrue(point_in_polygon(0.5, 0.5, square))
        self.assertFalse(point_in_polygon(0.05, 0.05, square))
        self.assertFalse(point_in_polygon(0.9, 0.95, square))

    def test_normalize_and_base_center(self) -> None:
        self.assertEqual(normalize_bbox(0, 0, 640, 360, 640, 360), (0.0, 0.0, 1.0, 1.0))
        self.assertEqual(bbox_base_center((0.4, 0.3, 0.6, 0.85)), (0.5, 0.85))
        self.assertTrue(bbox_base_center_visible((0.4, 0.3, 0.6, 0.85)))
        self.assertTrue(bbox_base_center_visible((0.4, -0.2, 0.6, 0.85)))
        self.assertFalse(bbox_base_center_visible((0.4, 0.3, 0.6, 1.0)))
        self.assertFalse(bbox_base_center_visible((1.1, 0.3, 1.3, 0.85)))


if __name__ == "__main__":
    unittest.main()
