import json
import unittest
from pathlib import Path

from vigia_edge_worker.evaluation import evaluate_dataset, load_samples, render_markdown


DATASET = Path(__file__).resolve().parents[1] / "datasets" / "cv-mini" / "v1"


class EvaluationTest(unittest.TestCase):
    def test_dataset_loads(self) -> None:
        samples = load_samples(DATASET)
        self.assertEqual(len(samples), 4)
        self.assertEqual(samples[0].id, "helmet-restricted-positive")

    def test_metrics_are_perfect_on_synthetic_dataset(self) -> None:
        result = evaluate_dataset(DATASET)
        self.assertEqual(result["tp"], 2)
        self.assertEqual(result["fp"], 0)
        self.assertEqual(result["fn"], 0)
        self.assertGreater(result["tn"], 0)
        self.assertEqual(result["precision"], 1.0)
        self.assertEqual(result["recall"], 1.0)
        self.assertIn("average_latency_ms", result)

    def test_markdown_contains_summary(self) -> None:
        result = evaluate_dataset(DATASET)
        md = render_markdown(result)
        self.assertIn("precision", md)
        self.assertIn("recall", md)
        self.assertIn("cv-mini", md)
        json.dumps(result)


if __name__ == "__main__":
    unittest.main()
