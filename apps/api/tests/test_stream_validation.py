import unittest

from vigia_api.domain.operations import classify_stream_source, validate_stream_identifier


class ClassifyStreamSourceTest(unittest.TestCase):
    def test_rtsp_and_rtmp(self):
        self.assertEqual(classify_stream_source("rtsp://10.0.0.2:554/live"), "rtsp")
        self.assertEqual(classify_stream_source("rtmp://host/app/stream"), "rtmp")

    def test_video_file_paths(self):
        self.assertEqual(classify_stream_source("assets/sample-ppe.mp4"), "video")
        self.assertEqual(classify_stream_source("file:///videos/demo.mov"), "video")
        self.assertEqual(classify_stream_source("/data/clip.webm?token=x"), "video")

    def test_http_stream_vs_hosted_video(self):
        self.assertEqual(classify_stream_source("http://cam/stream.mjpeg"), "http")
        self.assertEqual(classify_stream_source("https://cdn/clip.mp4"), "video")

    def test_invalid(self):
        self.assertIsNone(classify_stream_source(""))
        self.assertIsNone(classify_stream_source("   "))
        self.assertIsNone(classify_stream_source("camera-07"))


class ValidateStreamIdentifierTest(unittest.TestCase):
    def test_dev_accepts_video_and_live(self):
        self.assertEqual(validate_stream_identifier("assets/sample.mp4", "dev"), "video")
        self.assertEqual(validate_stream_identifier("rtsp://cam/live", "dev"), "rtsp")

    def test_production_requires_live_stream(self):
        self.assertEqual(validate_stream_identifier("rtsp://cam/live", "production"), "rtsp")
        with self.assertRaises(ValueError):
            validate_stream_identifier("assets/sample.mp4", "production")
        with self.assertRaises(ValueError):
            validate_stream_identifier("http://cam/stream.mjpeg", "staging")

    def test_invalid_raises_in_any_env(self):
        with self.assertRaises(ValueError):
            validate_stream_identifier("nonsense", "dev")


if __name__ == "__main__":
    unittest.main()
