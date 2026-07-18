from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import vigia_edge_worker.evaluation_real as evaluation_real


class _Detector:
    def __init__(self, *args, **kwargs):
        self.last_analysis = None
        self._queue: list[list[tuple[int, str]]] = []

    def load_context(self, payload):
        self.payload = payload

    def queue(self, entries):
        self._queue = list(entries)

    def detect(self, frame):
        labels = self._queue.pop(0) if self._queue else []
        self.last_analysis = {"boxes": [{"category": cat} for _cls, cat in labels]}
        events = []
        if any(cat == "person" for _cls, cat in labels):
            events.append("restricted_intrusion")
        if any(cat == "no_helmet" for _cls, cat in labels):
            events.append("ppe_violation")
        return [type("V", (), {"event_type": event})() for event in events]


def _write_yolo_dataset(root: Path) -> Path:
    (root / "images" / "train").mkdir(parents=True)
    (root / "labels" / "train").mkdir(parents=True)
    (root / "images" / "train" / "img1.jpg").write_bytes(b"a")
    (root / "images" / "train" / "img2.jpg").write_bytes(b"b")
    (root / "images" / "train" / "img3.jpg").write_bytes(b"c")
    (root / "labels" / "train" / "img1.txt").write_text("0 0.5 0.5 0.2 0.2\n2 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    (root / "labels" / "train" / "img2.txt").write_text("1 0.5 0.5 0.2 0.2\n", encoding="utf-8")
    (root / "labels" / "train" / "img3.txt").write_text("", encoding="utf-8")
    (root / "data.yaml").write_text("path: .\ntrain: images/train\nnames: [person, helmet, no-helmet]\n", encoding="utf-8")
    return root / "data.yaml"


def _write_manifest_dataset(root: Path) -> Path:
    for name in ("a.jpg", "b.jpg", "c.jpg"):
        (root / name).write_bytes(name.encode("utf-8"))
    manifest = {
        "version": "manifest-v1",
        "samples": [
            {"id": "s1", "file": "a.jpg", "pessoas_esperadas": 1, "pessoas_sem_capacete": 1, "pessoas_com_capacete": 0, "ha_violacao_epi": True, "scenario": "obra", "tags": ["night"]},
            {"id": "s2", "file": "b.jpg", "pessoas_esperadas": 1, "pessoas_sem_capacete": 0, "pessoas_com_capacete": 1, "ha_violacao_epi": False, "scenario": "obra", "tags": ["day"]},
            {"id": "s3", "file": "c.jpg", "pessoas_esperadas": 0, "pessoas_sem_capacete": 0, "pessoas_com_capacete": 0, "ha_violacao_epi": False, "scenario": "vazio", "tags": ["empty"]},
        ],
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root / "manifest.json"


class EvaluationRealTest(unittest.TestCase):
    def test_parse_simple_yaml_and_normalize_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = Path(tmp) / "data.yaml"
            yaml_path.write_text("train: images/train\nval: images/val\nnames:\n- person\n- no-helmet\n", encoding="utf-8")
            data = evaluation_real._parse_simple_yaml(yaml_path)
            self.assertEqual(data["train"], "images/train")
            self.assertEqual(data["names"], ["person", "no-helmet"])
            self.assertEqual(evaluation_real._category_for("NO-Hardhat"), "no_helmet")
            self.assertEqual(evaluation_real._category_for("person"), "person")

    def test_parse_yolo_names_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            yaml_path = Path(tmp) / "data.yaml"
            yaml_path.write_text("path: .\ntrain: images/train\nnames:\n  0: helmet\n  1: no-helmet\n  3: person\n", encoding="utf-8")
            data = evaluation_real._parse_simple_yaml(yaml_path)
            self.assertEqual(evaluation_real._normalize_names(data["names"]), ["helmet", "no-helmet", "", "person"])

    def test_yolo_dataset_metrics_and_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = _write_yolo_dataset(Path(tmp))
            fake = _Detector()
            fake.queue([
                [],
                [(0, "person"), (2, "no_helmet")],
                [],
                [(0, "person")],
            ])
            with patch.object(evaluation_real, "RealDetector", lambda *a, **k: fake):
                report = evaluation_real.avaliar(dataset, "/models/fake.pt", 0.4)
            self.assertEqual(report["dataset_mode"], "yolo")
            self.assertEqual(report["ppe_violation"]["tp"], 1)
            self.assertEqual(report["ppe_violation"]["fp"], 0)
            self.assertEqual(report["ppe_violation"]["fn"], 0)
            self.assertEqual(report["coverage_summary"]["helmet_samples"], 1)
            self.assertEqual(report["coverage_summary"]["empty_samples"], 2)
            self.assertEqual(report["coverage_summary"]["scenarios"], {"train": 3})
            self.assertGreaterEqual(report["latencia_ms"]["media"], 0)

    def test_manifest_per_scenario_metrics_and_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            dataset = _write_manifest_dataset(Path(tmp))
            fake = _Detector()
            fake.queue([
                [],
                [(0, "person"), (2, "no_helmet")],
                [(0, "person"), (1, "helmet")],
                [],
            ])
            with patch.object(evaluation_real, "RealDetector", lambda *a, **k: fake):
                report = evaluation_real.avaliar(dataset, "/models/fake.pt", 0.4)
            self.assertEqual(report["coverage_summary"]["helmet_samples"], 1)
            self.assertEqual(report["coverage_summary"]["empty_samples"], 1)
            self.assertEqual(report["epi_por_scenario"]["obra"]["sample_count"], 2)
            self.assertEqual(report["epi_por_scenario"]["vazio"]["sample_count"], 1)
            self.assertEqual(report["epi_por_scenario"]["obra"]["epi_violation"]["tp"], 1)
            self.assertEqual(report["epi_por_scenario"]["vazio"]["epi_violation"]["tn"], 1)
            self.assertEqual(report["epi_por_scenario"]["obra"]["restricted_intrusion_proxy"]["tp"], 2)
            self.assertEqual(report["restricted_intrusion_proxy"]["tp"], 2)
            self.assertEqual(report["restricted_intrusion_proxy"]["tn"], 1)
            self.assertEqual(report["no_helmet_detection_por_frame"]["tp"], 1)
            self.assertEqual(report["no_helmet_detection_por_frame"]["fp"], 0)
            self.assertEqual(report["no_helmet_detection_por_frame"]["tn"], 2)

    def test_threshold_helper_passes_and_fails(self):
        ok = {"coverage_summary": {"total_samples": 3, "helmet_samples": 1, "empty_samples": 1}, "ppe_violation": {"recall": 0.5}}
        self.assertEqual(evaluation_real.check_report_thresholds(ok, min_samples=2, min_helmet_samples=1, min_empty_samples=1, min_ppe_recall=0.4), [])
        bad = evaluation_real.check_report_thresholds(ok, min_samples=4, min_helmet_samples=2, min_empty_samples=2, min_ppe_recall=0.6)
        self.assertIn("sample_count<4", bad)
        self.assertIn("helmet_samples<2", bad)
        self.assertIn("empty_samples<2", bad)
        self.assertIn("ppe_recall<0.6", bad)


if __name__ == "__main__":
    unittest.main()
