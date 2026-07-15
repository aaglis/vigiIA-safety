import json
import unittest

from vigia_edge_worker.config import default_config
from vigia_edge_worker.events import validate_detection_event, validate_heartbeat_event
from vigia_edge_worker.heartbeat import build_heartbeat
from vigia_edge_worker.mock_detector import detect_once


class EventsTest(unittest.TestCase):
    def test_mock_detection_has_required_fields(self) -> None:
        event = detect_once(default_config()).to_dict()
        validate_detection_event(event)
        self.assertEqual(event["event_type"], "mock_detection")
        self.assertEqual(event["confidence"], 0.92)
        json.dumps(event)

    def test_heartbeat_has_required_fields(self) -> None:
        heartbeat = build_heartbeat(default_config(), processed_frames=1, emitted_events=1).to_dict()
        validate_heartbeat_event(heartbeat)
        self.assertEqual(heartbeat["status"]["state"], "ok")
        self.assertEqual(heartbeat["status"]["processed_frames"], 1)
        self.assertEqual(heartbeat["status"]["emitted_events"], 1)
        json.dumps(heartbeat)


if __name__ == "__main__":
    unittest.main()
