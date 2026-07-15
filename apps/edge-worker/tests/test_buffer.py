import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from vigia_edge_worker.buffer import DetectionBuffer


class BufferTest(unittest.TestCase):
    def test_enqueue_persist_and_mark_sent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            buf = DetectionBuffer(tmp, max_attempts=3, backoff_seconds=1)
            buf.enqueue({"event_id": "evt-1", "camera_id": "cam-1"})
            self.assertTrue((Path(tmp) / "pending" / "evt-1.json").exists())
            reloaded = DetectionBuffer(tmp, max_attempts=3, backoff_seconds=1)
            loaded = reloaded.load("evt-1")
            assert loaded is not None
            self.assertEqual(loaded.status, "pending")
            reloaded.mark_sent("evt-1")
            self.assertTrue((Path(tmp) / "sent" / "evt-1.json").exists())

    def test_backoff_and_failure_rotation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            buf = DetectionBuffer(tmp, max_attempts=2, backoff_seconds=2)
            buf.enqueue({"event_id": "evt-1", "camera_id": "cam-1"})
            failed = buf.mark_failed("evt-1", {"event_id": "evt-1"}, "boom", attempts=1)
            self.assertEqual(failed.status, "pending")
            due = buf.due(now=datetime.now(timezone.utc) + timedelta(seconds=3))
            self.assertEqual([item.event_id for item in due], ["evt-1"])
            final = buf.mark_failed("evt-1", {"event_id": "evt-1"}, "boom", attempts=2)
            self.assertEqual(final.status, "failed")
            self.assertTrue((Path(tmp) / "failed" / "evt-1.json").exists())


if __name__ == "__main__":
    unittest.main()
