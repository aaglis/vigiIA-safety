#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "edge-worker" / "src"))

check_report_thresholds = importlib.import_module("vigia_edge_worker.evaluation_real").check_report_thresholds


def main() -> int:
    parser = argparse.ArgumentParser(description="Check evaluation report thresholds.")
    parser.add_argument("report", type=Path)
    parser.add_argument("--min-samples", type=int, default=0)
    parser.add_argument("--min-helmet-samples", type=int, default=0)
    parser.add_argument("--min-empty-samples", type=int, default=0)
    parser.add_argument("--min-ppe-recall", type=float, default=0.0)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    failures = check_report_thresholds(
        report,
        min_samples=args.min_samples,
        min_helmet_samples=args.min_helmet_samples,
        min_empty_samples=args.min_empty_samples,
        min_ppe_recall=args.min_ppe_recall,
    )
    if failures:
        print(json.dumps({"status": "failed", "reasons": failures}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "passed"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
