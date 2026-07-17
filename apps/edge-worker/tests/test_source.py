import tempfile
import unittest
from pathlib import Path

from vigia_edge_worker.config import WorkerConfig
from vigia_edge_worker.source import FrameSourceError, build_frame_source


class SourceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = WorkerConfig(edge_worker_id="worker-1", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="zone-1")

    def test_mock_source_yields_synthetic_frame(self) -> None:
        source = build_frame_source(self.config)
        frame = next(source.frames())
        self.assertEqual(frame.metadata["source_type"], "mock")
        self.assertEqual(frame.camera_id, "cam-1")

    def test_image_source_missing_file_fails_clear(self) -> None:
        cfg = WorkerConfig(edge_worker_id="worker-1", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="zone-1", edge_source_type="image", edge_source_uri="/no/such/file.jpg")
        source = build_frame_source(cfg)
        with self.assertRaises(FrameSourceError):
            list(source.frames())

    def test_image_source_reads_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frame.jpg"
            path.write_bytes(b"helmet frame bytes")
            cfg = WorkerConfig(edge_worker_id="worker-1", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="zone-1", edge_source_type="image", edge_source_uri=str(path))
            source = build_frame_source(cfg)
            frame = next(source.frames())
            self.assertEqual(frame.image_bytes, b"helmet frame bytes")
            self.assertEqual(frame.metadata["source_type"], "image")

    def test_image_source_directory_yields_multiple_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "0001.jpg").write_bytes(b"frame-1")
            (d / "0002.jpg").write_bytes(b"frame-2")
            cfg = WorkerConfig(edge_worker_id="worker-1", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="zone-1", edge_source_type="image", edge_source_uri=str(d))
            frames = list(build_frame_source(cfg).frames())
            self.assertEqual(len(frames), 2)
            self.assertEqual(frames[0].metadata["source_type"], "image")

    def test_rtsp_builds_cv2_source(self) -> None:
        from vigia_edge_worker.source import Cv2VideoSource
        cfg = WorkerConfig(edge_worker_id="worker-1", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="zone-1", edge_source_type="rtsp", edge_source_uri="rtsp://camera")
        self.assertIsInstance(build_frame_source(cfg), Cv2VideoSource)

    def test_missing_video_file_fails_clear(self) -> None:
        cfg = WorkerConfig(edge_worker_id="worker-1", organization_id="org-1", site_id="site-1", camera_id="cam-1", zone_id="zone-1", edge_source_type="video", edge_source_uri="/no/such/video.mp4")
        with self.assertRaises(FrameSourceError):
            list(build_frame_source(cfg).frames())

    def test_config_stream_override_drives_source(self) -> None:
        from vigia_edge_worker.source import Cv2VideoSource, classify_source_type
        self.assertEqual(classify_source_type("rtsp://cam/live"), "rtsp")
        self.assertEqual(classify_source_type("/videos/x.mp4"), "video")
        source = build_frame_source(self.config, stream_override="/videos/demo.mp4")
        self.assertIsInstance(source, Cv2VideoSource)
        self.assertEqual(source.source_uri, "/videos/demo.mp4")


if __name__ == "__main__":
    unittest.main()
