import unittest
from dataclasses import dataclass
from typing import Any, cast
from unittest.mock import patch
import tempfile
from pathlib import Path
import os

from vigia_edge_worker.buffer import DetectionBuffer
from vigia_edge_worker.config import WorkerConfig
from vigia_edge_worker.detector import DetectionResult, FrameInput
from vigia_edge_worker.rules import RuleEngine
import vigia_edge_worker.main as main_mod
from vigia_edge_worker.config import default_config


@dataclass
class FakeSource:
    frames_data: list[FrameInput]

    def frames(self):
        for frame in self.frames_data:
            yield frame


class FakeDetector:
    def detect(self, frame: FrameInput):
        return [DetectionResult(event_type="real_detection", confidence=0.88, model_version="real-cv-0", zone_id="zone-1", metadata={"cv_mode": "real"})]


class FakeAnalysisDetector(FakeDetector):
    def __init__(self, last_analysis: dict[str, Any] | None = None) -> None:
        self.last_analysis = last_analysis


class MultiResultDetector:
    def __init__(self, results: list[DetectionResult]) -> None:
        self.results = results

    def detect(self, frame: FrameInput):
        return self.results


class RecordingRules:
    def __init__(self, applied_by_event: dict[str, Any]) -> None:
        self.applied_by_event = applied_by_event
        self.calls: list[tuple[str, str]] = []

    def apply(self, frame: FrameInput, result: DetectionResult):
        self.calls.append((frame.timestamp, result.event_type))
        return self.applied_by_event.get(result.event_type)


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

    def test_frame_analysis_fps_parsing_is_clamped(self) -> None:
        original = {key: os.environ.get(key) for key in ["EDGE_FRAME_ANALYSIS_FPS"]}
        try:
            os.environ.pop("EDGE_FRAME_ANALYSIS_FPS", None)
            self.assertEqual(default_config().edge_frame_analysis_fps, 2.0)
            os.environ["EDGE_FRAME_ANALYSIS_FPS"] = "0"
            self.assertEqual(default_config().edge_frame_analysis_fps, 1.0)
            os.environ["EDGE_FRAME_ANALYSIS_FPS"] = "10"
            self.assertEqual(default_config().edge_frame_analysis_fps, 5.0)
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_frame_analysis_skip_when_detector_has_no_analysis(self) -> None:
        frame = FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", metadata={"source_type": "image"})

        class Client:
            def __init__(self) -> None:
                self.publish_calls = 0

            def request_evidence_upload(self, file_id, incident_id=None):
                return {"upload_path": f"org/org-1/edge-workers/worker-1/evidence/{file_id}"}

            def upload_evidence_bytes(self, upload_ref, data, content_type="application/octet-stream"):
                return {"status": "uploaded"}

            def send_detection(self, payload):
                return {"ok": True}

            def send_detection_with_retry(self, payload, attempts=1):
                return self.send_detection(payload)

            def publish_frame_analysis(self, payload):
                self.publish_calls += 1

            def send_heartbeat(self, payload):
                return {"ok": True}

        client = Client()
        detector = FakeAnalysisDetector(last_analysis=None)
        with patch("vigia_edge_worker.main.time.monotonic", side_effect=[0.0, 0.0, 1.0]), patch("vigia_edge_worker.main.time.perf_counter", return_value=0.0):
            run_pipeline = cast(Any, getattr(main_mod, "_run_pipeline"))
            run_pipeline(self.config, type("Sel", (), {"cv_mode": "real"})(), detector, FakeSource([frame]), client=client, api_mode=True, buffer=None)
        self.assertEqual(client.publish_calls, 0)

    def test_frame_analysis_throttles_independently_of_detection(self) -> None:
        frames = [FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp=f"2026-01-01T00:00:0{i}Z", metadata={"source_type": "image"}) for i in range(10)]

        class Client:
            def __init__(self) -> None:
                self.publish_calls: list[dict[str, Any]] = []

            def request_evidence_upload(self, file_id, incident_id=None):
                return {"upload_path": f"org/org-1/edge-workers/worker-1/evidence/{file_id}"}

            def upload_evidence_bytes(self, upload_ref, data, content_type="application/octet-stream"):
                return {"status": "uploaded"}

            def send_detection(self, payload):
                return {"ok": True}

            def send_detection_with_retry(self, payload, attempts=1):
                return self.send_detection(payload)

            def publish_frame_analysis(self, payload):
                self.publish_calls.append(payload)

            def send_heartbeat(self, payload):
                return {"ok": True}

        detector = FakeAnalysisDetector(last_analysis={"boxes": [], "violations": []})
        client = Client()
        monotonic_values = [0.0]
        for i in range(1, 11):
            monotonic_values.extend([i * 0.1, i * 0.1])
        perf_values = [float(i) for i in range(40)]
        with patch("vigia_edge_worker.main.time.monotonic", side_effect=monotonic_values), patch("vigia_edge_worker.main.time.perf_counter", side_effect=perf_values):
            run_pipeline = cast(Any, getattr(main_mod, "_run_pipeline"))
            result = run_pipeline(self.config, type("Sel", (), {"cv_mode": "real"})(), detector, FakeSource(frames), client=client, api_mode=True, buffer=None)
        self.assertEqual(result["processed_frames"], 10)
        self.assertEqual(len(client.publish_calls), 2)
        self.assertEqual(client.publish_calls[0]["camera_id"], "cam-1")
        self.assertEqual(client.publish_calls[0]["boxes"], [])

    def test_frame_analysis_publish_failure_is_non_fatal(self) -> None:
        frame = FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", metadata={"source_type": "image"})

        class Client:
            def __init__(self) -> None:
                self.publish_calls = 0

            def request_evidence_upload(self, file_id, incident_id=None):
                return {"upload_path": f"org/org-1/edge-workers/worker-1/evidence/{file_id}"}

            def upload_evidence_bytes(self, upload_ref, data, content_type="application/octet-stream"):
                return {"status": "uploaded"}

            def send_detection(self, payload):
                return {"ok": True}

            def send_detection_with_retry(self, payload, attempts=1):
                return self.send_detection(payload)

            def publish_frame_analysis(self, payload):
                self.publish_calls += 1
                raise RuntimeError("overlay down")

            def send_heartbeat(self, payload):
                return {"ok": True}

        client = Client()
        detector = FakeAnalysisDetector(last_analysis={"boxes": [], "violations": []})
        with patch("vigia_edge_worker.main.time.monotonic", side_effect=[0.0, 0.0, 1.0]), patch("vigia_edge_worker.main.time.perf_counter", return_value=0.0):
            run_pipeline = cast(Any, getattr(main_mod, "_run_pipeline"))
            result = run_pipeline(self.config, type("Sel", (), {"cv_mode": "real"})(), detector, FakeSource([frame]), client=client, api_mode=True, buffer=None)
        self.assertEqual(result["processed_frames"], 1)
        self.assertEqual(client.publish_calls, 1)

    def test_pipeline_emits_every_allowed_result_and_reuses_one_evidence_upload(self) -> None:
        frame = FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", image_bytes=b"frame-bytes", metadata={"source_type": "image"})
        results = [
            DetectionResult(event_type="violation-a", confidence=0.91, model_version="real-cv-0", zone_id="zone-1", evidence={"annotated_jpeg": b"raw-a"}, annotated_jpeg=b"raw-a"),
            DetectionResult(event_type="violation-b", confidence=0.83, model_version="real-cv-0", zone_id="zone-2", evidence={"annotated_jpeg": b"raw-b"}, annotated_jpeg=b"raw-b"),
        ]

        class Client:
            def __init__(self) -> None:
                self.request_calls: list[str] = []
                self.upload_calls: list[bytes] = []
                self.detections: list[dict[str, Any]] = []

            def request_evidence_upload(self, file_id, incident_id=None):
                self.request_calls.append(file_id)
                return {"upload_url": "https://upload.local/file", "upload_path": f"org/org-1/edge-workers/worker-1/evidence/{file_id}"}

            def upload_evidence_bytes(self, upload_ref, data, content_type="application/octet-stream"):
                self.upload_calls.append(data)
                return {"ok": True}

            def send_detection(self, payload):
                self.detections.append(payload)
                return {"ok": True}

            def send_detection_with_retry(self, payload, attempts=1):
                return self.send_detection(payload)

            def send_heartbeat(self, payload):
                return {"ok": True}

        rules = RecordingRules({
            "violation-a": type("Applied", (), {"event_type": "restricted_intrusion", "severity": "high", "summary": "A", "zone_id": "zone-1", "metadata": {"rule": "A"}})(),
            "violation-b": type("Applied", (), {"event_type": "restricted_intrusion", "severity": "high", "summary": "B", "zone_id": "zone-2", "metadata": {"rule": "B"}})(),
        })
        run_pipeline = cast(Any, getattr(main_mod, "_run_pipeline"))
        client = Client()
        result = run_pipeline(self.config, type("Sel", (), {"cv_mode": "real"})(), MultiResultDetector(results), FakeSource([frame]), rules=rules, client=client, api_mode=True, buffer=None)

        self.assertEqual(result["emitted_events"], 2)
        self.assertEqual([d["event_type"] for d in result["detections"]], ["restricted_intrusion", "restricted_intrusion"])
        self.assertEqual(len(client.request_calls), 1)
        self.assertEqual(len(client.upload_calls), 1)
        self.assertEqual(len(client.detections), 2)
        self.assertEqual(client.detections[0]["evidence"], client.detections[1]["evidence"])
        self.assertEqual(client.detections[0]["evidence"]["upload_path"], client.detections[1]["evidence"]["upload_path"])

    def test_pipeline_same_frame_allows_distinct_same_key_events_but_cools_down_later(self) -> None:
        frame_1 = FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", metadata={"source_type": "image"})
        frame_2 = FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:01Z", metadata={"source_type": "image"})
        result_a = DetectionResult(event_type="restricted_intrusion", confidence=0.91, model_version="real-cv-0", zone_id="zone-1")
        result_b = DetectionResult(event_type="restricted_intrusion", confidence=0.83, model_version="real-cv-0", zone_id="zone-1")

        class Client:
            def request_evidence_upload(self, file_id, incident_id=None):
                return {"upload_path": f"org/org-1/edge-workers/worker-1/evidence/{file_id}"}

            def upload_evidence_bytes(self, upload_ref, data, content_type="application/octet-stream"):
                return {"ok": True}

            def send_detection(self, payload):
                return {"ok": True}

            def send_detection_with_retry(self, payload, attempts=1):
                return self.send_detection(payload)

            def send_heartbeat(self, payload):
                return {"ok": True}

        rules = RuleEngine(cooldown_seconds=10)
        rules.load_context({"site_id": "site-1", "allowed_camera_ids": ["cam-1"], "zones": [{"id": "zone-1", "zone_type": "restricted"}]})

        run_pipeline = cast(Any, getattr(main_mod, "_run_pipeline"))
        first = run_pipeline(self.config, type("Sel", (), {"cv_mode": "real"})(), MultiResultDetector([result_a, result_b]), FakeSource([frame_1]), rules=rules, client=Client(), api_mode=True, buffer=None)
        second = run_pipeline(self.config, type("Sel", (), {"cv_mode": "real"})(), MultiResultDetector([result_a]), FakeSource([frame_2]), rules=rules, client=Client(), api_mode=True, buffer=None)

        self.assertEqual(first["emitted_events"], 2)
        self.assertEqual([d["event_type"] for d in first["detections"]], ["restricted_intrusion", "restricted_intrusion"])
        self.assertEqual(second["emitted_events"], 0)

    def test_suppressed_result_does_not_reuse_raw_detector_jpeg_for_uploaded_evidence(self) -> None:
        frame = FrameInput(camera_id="cam-1", site_id="site-1", organization_id="org-1", timestamp="2026-01-01T00:00:00Z", image_bytes=b"frame-bytes", metadata={"source_type": "image"})
        allowed = DetectionResult(event_type="violation-a", confidence=0.91, model_version="real-cv-0", zone_id="zone-1", evidence={"annotated_jpeg": b"allowed-jpeg"}, annotated_jpeg=b"allowed-jpeg")
        suppressed = DetectionResult(event_type="violation-b", confidence=0.83, model_version="real-cv-0", zone_id="zone-2", evidence={"annotated_jpeg": b"suppressed-raw-jpeg"}, annotated_jpeg=b"suppressed-raw-jpeg")

        class Client:
            def __init__(self) -> None:
                self.upload_calls: list[bytes] = []

            def request_evidence_upload(self, file_id, incident_id=None):
                return {"upload_url": "https://upload.local/file", "upload_path": f"org/org-1/edge-workers/worker-1/evidence/{file_id}"}

            def upload_evidence_bytes(self, upload_ref, data, content_type="application/octet-stream"):
                self.upload_calls.append(data)
                return {"ok": True}

            def send_detection(self, payload):
                return {"ok": True}

            def send_detection_with_retry(self, payload, attempts=1):
                return self.send_detection(payload)

            def send_heartbeat(self, payload):
                return {"ok": True}

        rules = RecordingRules({
            "violation-a": type("Applied", (), {"event_type": "restricted_intrusion", "severity": "high", "summary": "A", "zone_id": "zone-1", "metadata": {}})(),
            "violation-b": None,
        })

        run_pipeline = cast(Any, getattr(main_mod, "_run_pipeline"))
        client = Client()
        result = run_pipeline(self.config, type("Sel", (), {"cv_mode": "real"})(), MultiResultDetector([allowed, suppressed]), FakeSource([frame]), rules=rules, client=client, api_mode=True, buffer=None)

        self.assertEqual(result["emitted_events"], 1)
        self.assertEqual(len(client.upload_calls), 1)
        self.assertNotEqual(client.upload_calls[0], suppressed.annotated_jpeg)
        self.assertEqual(client.upload_calls[0], b"frame-bytes")


if __name__ == "__main__":
    unittest.main()
