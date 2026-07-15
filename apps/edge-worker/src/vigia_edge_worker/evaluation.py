from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from .config import WorkerConfig
from .detector import FrameInput
from .real_detector import RealDetector, RealDetectorConfig


@dataclass(frozen=True)
class EvaluationSample:
    id: str
    file: str
    expected_detection: bool
    marker: str
    expected_zone_id: str | None = None
    expected_event_type: str | None = None
    class_label: str | None = None
    notes: str | None = None


def load_manifest(dataset_dir: str | Path) -> dict[str, Any]:
    dataset_dir = Path(dataset_dir)
    return json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))


def load_samples(dataset_dir: str | Path) -> list[EvaluationSample]:
    manifest = load_manifest(dataset_dir)
    return [EvaluationSample(id=s["id"], file=s["file"], expected_detection=bool(s["expected_detection"]), marker=str(s.get("marker") or manifest.get("default_marker", "helmet")), expected_zone_id=s.get("expected_zone_id"), expected_event_type=s.get("expected_event_type"), class_label=s.get("class"), notes=s.get("notes")) for s in manifest["samples"]]


def evaluate_dataset(dataset_dir: str | Path) -> dict[str, Any]:
    dataset_dir = Path(dataset_dir)
    manifest = load_manifest(dataset_dir)
    samples = load_samples(dataset_dir)
    config = WorkerConfig(edge_worker_id="eval-worker", organization_id="org-eval", site_id="site-eval", camera_id="cam-eval", zone_id="zone-critical")
    model_version = str(manifest.get("model_version", "real-cv-eval"))
    tp = fp = fn = tn = 0
    latencies_ms: list[float] = []
    per_sample: list[dict[str, Any]] = []
    for sample in samples:
        frame_path = dataset_dir / sample.file
        frame_bytes = frame_path.read_bytes()
        detector = RealDetector(config, RealDetectorConfig(enabled=True, marker=sample.marker, model_version=model_version))
        frame = FrameInput(camera_id="cam-eval", site_id="site-eval", organization_id="org-eval", timestamp="2026-01-01T00:00:00Z", image_bytes=frame_bytes, metadata={"source_type": "dataset", "sample_id": sample.id, "cv_marker": sample.marker})
        started = perf_counter()
        detections = detector.detect(frame)
        elapsed_ms = (perf_counter() - started) * 1000
        latencies_ms.append(elapsed_ms)
        predicted = bool(detections)
        if predicted and sample.expected_detection:
            tp += 1
        elif predicted and not sample.expected_detection:
            fp += 1
        elif not predicted and sample.expected_detection:
            fn += 1
        else:
            tn += 1
        per_sample.append({"id": sample.id, "predicted": predicted, "expected": sample.expected_detection, "latency_ms": round(elapsed_ms, 4)})
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    avg_latency_ms = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0
    return {"dataset": manifest.get("dataset", "unknown"), "version": manifest.get("version", "unknown"), "samples": len(samples), "tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": round(precision, 4), "recall": round(recall, 4), "average_latency_ms": round(avg_latency_ms, 4), "criteria": manifest.get("criteria", {}), "per_sample": per_sample}


def render_markdown(result: dict[str, Any]) -> str:
    lines = [f"# CV evaluation: {result['dataset']} {result['version']}", "", f"- samples: {result['samples']}", f"- tp: {result['tp']}  fp: {result['fp']}  fn: {result['fn']}  tn: {result['tn']}", f"- precision: {result['precision']}", f"- recall: {result['recall']}", f"- average_latency_ms: {result['average_latency_ms']}"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m vigia_edge_worker.evaluation")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args(argv)
    result = evaluate_dataset(args.dataset)
    if args.format == "markdown":
        print(render_markdown(result))
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
