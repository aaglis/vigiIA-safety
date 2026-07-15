import unittest

from vigia_edge_worker.config import WorkerConfig
from vigia_edge_worker.heartbeat import build_heartbeat
from vigia_edge_worker.telemetry import TelemetryState, sanitize_error


class TelemetryTest(unittest.TestCase):
    def test_heartbeat_contains_telemetry_fields(self) -> None:
        cfg = WorkerConfig(edge_worker_id="worker-1", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="zone-1", worker_version="1.2.3", cv_mode="real", edge_source_type="image")
        telemetry = TelemetryState(cv_mode="real", source_type="image", worker_version="1.2.3")
        telemetry.record_inference_latency(2.0)
        telemetry.record_send_latency(3.0)
        telemetry.pending_queue = 4
        telemetry.record_error("postgresql://user:secret@db.local/app?password=secret", kind="api")
        hb = build_heartbeat(cfg, processed_frames=9, emitted_events=2, telemetry=telemetry, pending_queue=4, last_error=telemetry.last_error).to_dict()
        status = hb["status"]
        self.assertEqual(status["cv_mode"], "real")
        self.assertEqual(status["source_type"], "image")
        self.assertEqual(status["pending_queue"], 4)
        self.assertEqual(status["processed_frames"], 9)
        self.assertEqual(status["emitted_events"], 2)
        self.assertIn("avg_inference_latency_ms", status)
        self.assertIn("avg_send_latency_ms", status)
        self.assertNotIn("secret", str(hb))

    def test_sanitize_error_masks_credentials(self) -> None:
        self.assertEqual(sanitize_error("postgresql://user:secret@db.local/app?password=secret"), "***")
        self.assertEqual(sanitize_error("api_key=dev-secret"), "***")


if __name__ == "__main__":
    unittest.main()
