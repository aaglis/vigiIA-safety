import unittest
from dataclasses import dataclass
from typing import Any, cast
from unittest.mock import patch
import tempfile

from vigia_edge_worker.buffer import DetectionBuffer
from vigia_edge_worker.config import WorkerConfig
from vigia_edge_worker.detector import DetectionResult, FrameInput
import vigia_edge_worker.main as main_mod


@dataclass
class FakeSource:
    frames_data: list[FrameInput]

    def frames(self):
        for frame in self.frames_data:
            yield frame


class FakeDetector:
    def detect(self, frame: FrameInput):
        return [DetectionResult(event_type="real_detection", confidence=0.88, model_version="real-cv-0", zone_id="zone-1", metadata={"cv_mode": "real"})]


class MainLoopTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = WorkerConfig(edge_worker_id="worker-1", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="zone-1")

    def test_run_once_processes_single_frame(self) -> None:
        source = FakeSource([FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", metadata={"source_type": "image"})])
        run_pipeline = cast(Any, getattr(main_mod, "_run_pipeline"))
        result = run_pipeline(self.config, type("Sel", (), {"cv_mode": "real"})(), FakeDetector(), source, api_mode=False)
        self.assertEqual(result["processed_frames"], 1)
        self.assertEqual(result["emitted_events"], 1)
        self.assertEqual(result["detections"][0]["metadata"]["source_type"], "image")

    def test_max_frames_limits_loop(self) -> None:
        cfg = WorkerConfig(edge_worker_id="worker-1", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="zone-1", edge_max_frames=1)
        source = FakeSource([
            FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", metadata={"source_type": "video"}),
            FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:01Z", metadata={"source_type": "video"}),
        ])
        run_pipeline = cast(Any, getattr(main_mod, "_run_pipeline"))
        result = run_pipeline(cfg, type("Sel", (), {"cv_mode": "real"})(), FakeDetector(), source, api_mode=False)
        self.assertEqual(result["processed_frames"], 1)

    def test_evidence_payload_keeps_local_paths_out(self) -> None:
        frame = FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", image_bytes=b"helmet bytes", metadata={"source_type": "image", "source_path": "/tmp/secret.jpg"})
        evidence_payload = cast(Any, getattr(main_mod, "_evidence_payload"))
        snapshot = evidence_payload(self.config, frame, upload_path="org/org-1/edge-workers/worker-1/evidence/file-1", file_id="file-1")
        self.assertEqual(snapshot["file_id"], "file-1")
        self.assertEqual(snapshot["source_type"], "image")
        self.assertNotIn("source_path", snapshot)

    def test_pipeline_uses_buffer_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            buffer = DetectionBuffer(tmp, max_attempts=3, backoff_seconds=1)
            class Client:
                def __init__(self) -> None:
                    self.calls = 0

                def request_evidence_upload(self, file_id, incident_id=None):
                    return {"upload_path": f"org/org-1/edge-workers/worker-1/evidence/{file_id}"}

                def send_detection(self, payload):
                    self.calls += 1
                    if self.calls == 1:
                        raise RuntimeError("transient")
                    return {"ok": True}

                def send_detection_with_retry(self, payload, attempts=1):
                    return self.send_detection(payload)

                def send_heartbeat(self, payload):
                    return {"ok": True}

            with patch.object(main_mod, "build_frame_source", return_value=FakeSource([FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", metadata={"source_type": "mock"})])), patch.object(main_mod, "RuleEngine") as rule_engine_cls:
                rule_engine = rule_engine_cls.return_value
                rule_engine.apply.return_value = None
                run_pipeline = cast(Any, getattr(main_mod, "_run_pipeline"))
                result = run_pipeline(self.config, type("Sel", (), {"cv_mode": "real"})(), FakeDetector(), FakeSource([FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", metadata={"source_type": "mock"})]), client=Client(), api_mode=True, buffer=buffer)
                self.assertEqual(result["emitted_events"], 1)
                self.assertGreater(len(list((Path := __import__('pathlib').Path)(tmp).glob('pending/*.json')) ) + len(list((Path)(tmp).glob('failed/*.json'))), 0)

    def test_pipeline_buffers_detection_when_api_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            buffer = DetectionBuffer(tmp, max_attempts=3, backoff_seconds=1)

            class OfflineClient:
                def request_evidence_upload(self, file_id, incident_id=None):
                    raise RuntimeError("api down")

                def send_detection_with_retry(self, payload, attempts=1):
                    raise RuntimeError("api down")

                def send_heartbeat(self, payload):
                    raise RuntimeError("api down")

            run_pipeline = cast(Any, getattr(main_mod, "_run_pipeline"))
            result = run_pipeline(self.config, type("Sel", (), {"cv_mode": "real"})(), FakeDetector(), FakeSource([FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", metadata={"source_type": "mock"})]), client=OfflineClient(), api_mode=True, buffer=buffer)

            self.assertEqual(result["emitted_events"], 1)
            event_id = result["detections"][0]["event_id"]
            buffered = buffer.load(event_id)
            assert buffered is not None
            self.assertEqual(buffered.status, "pending")
            self.assertEqual(buffered.payload["event_id"], event_id)
            self.assertNotIn("upload_path", buffered.payload["evidence"])

    def test_binary_evidence_upload_is_attached_and_failure_is_non_blocking(self) -> None:
        class UploadClient:
            def request_evidence_upload(self, file_id, incident_id=None):
                return {"upload_url": "https://upload.local/file", "upload_path": f"org/org-1/edge-workers/worker-1/evidence/{file_id}"}

            def upload_evidence_bytes(self, upload_ref, data, content_type="application/octet-stream"):
                raise RuntimeError("upload down")

            def send_detection(self, payload):
                return {"ok": True}

            def send_detection_with_retry(self, payload, attempts=1):
                return self.send_detection(payload)

            def send_heartbeat(self, payload):
                return {"ok": True}

        source = FakeSource([FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", image_bytes=b"helmet bytes", metadata={"source_type": "image"})])
        run_pipeline = cast(Any, getattr(main_mod, "_run_pipeline"))
        result = run_pipeline(self.config, type("Sel", (), {"cv_mode": "real"})(), FakeDetector(), source, client=UploadClient(), api_mode=True, buffer=None)
        evidence = result["detections"][0]["evidence"]
        self.assertEqual(evidence["upload_status"], "failed")
        self.assertIn("upload_error", evidence)
        self.assertEqual(evidence["size"], len(b"helmet bytes"))


if __name__ == "__main__":
    unittest.main()
