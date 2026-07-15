import json
import unittest
from pathlib import Path
import sys

EDGE_SRC = Path(__file__).resolve().parents[2] / "edge-worker" / "src"
if str(EDGE_SRC) not in sys.path:
    sys.path.insert(0, str(EDGE_SRC))

from vigia_edge_worker.config import default_config
from vigia_edge_worker.events import validate_detection_event, validate_heartbeat_event
from vigia_edge_worker.heartbeat import build_heartbeat
from vigia_edge_worker.mock_detector import detect_once

from vigia_api.domain.incidents import parse_detection_event


class ContractAlignmentTest(unittest.TestCase):
    def test_detection_event_matches_schema_keys(self) -> None:
        payload = detect_once(default_config()).to_dict()
        validate_detection_event(payload)
        self.assertEqual(set(payload), {"event_id", "camera_id", "site_id", "organization_id", "timestamp", "event_type", "zone_id", "confidence", "model_version", "worker_id", "evidence"})
        schema = json.loads((Path(__file__).resolve().parents[3] / "packages" / "contracts" / "events" / "detection-event.v1.schema.json").read_text())
        self.assertEqual(schema["additionalProperties"], False)

    def test_heartbeat_event_matches_schema_keys(self) -> None:
        payload = build_heartbeat(default_config(), processed_frames=1, emitted_events=1).to_dict()
        validate_heartbeat_event(payload)
        self.assertEqual(set(payload), {"client_id", "organization_id", "site_id", "sent_at", "status", "version"})
        self.assertIsInstance(payload["status"], dict)
        self.assertEqual(payload["status"]["state"], "ok")

    def test_parse_detection_timestamp_becomes_detected_at(self) -> None:
        payload = {
            "organization_id": "org-1",
            "camera_id": "cam-1",
            "zone_id": "zone-1",
            "severity": "high",
            "timestamp": "2026-01-01T00:00:00Z",
            "event_type": "mock_detection",
            "confidence": 0.9,
            "site_id": "site-1",
            "worker_id": "worker-1",
        }
        event = parse_detection_event(payload)
        self.assertEqual(event.event_type, "mock_detection")
        self.assertEqual(event.site_id, "site-1")
        self.assertEqual(event.worker_id, "worker-1")
        self.assertEqual(event.detected_at.isoformat(), "2026-01-01T00:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
