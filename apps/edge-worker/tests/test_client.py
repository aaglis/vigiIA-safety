import json
import unittest

from vigia_edge_worker.client import EdgeApiClient


class EdgeApiClientTest(unittest.TestCase):
    def test_request_uses_expected_headers_and_json_body(self) -> None:
        captured = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"{\"ok\": true}"

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["data"] = request.data
            captured["timeout"] = timeout
            return Response()

        client = EdgeApiClient("http://api:8000/api/v1", "client-123", "secret-key", timeout=7, opener=fake_urlopen, request_id="req-1")
        result = client.send_detection({"camera_id": "cam-1"})

        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["url"], "http://api:8000/api/v1/edge-workers/me/detections")
        self.assertEqual(captured["timeout"], 7)
        self.assertEqual(captured["headers"]["X-edge-client-id"], "client-123")
        self.assertEqual(captured["headers"]["X-edge-api-key"], "secret-key")
        self.assertEqual(captured["headers"]["X-request-id"], "req-1")
        self.assertEqual(json.loads(captured["data"].decode("utf-8")), {"camera_id": "cam-1"})

    def test_http_error_is_masked(self) -> None:
        from urllib.error import HTTPError

        def fake_urlopen(*args, **kwargs):
            raise HTTPError("http://api", 403, "Forbidden", hdrs=None, fp=None)  # type: ignore[arg-type]

        client = EdgeApiClient("http://api:8000/api/v1", "client-123", "secret-key", opener=fake_urlopen)
        with self.assertRaises(RuntimeError) as ctx:
            client.get_config()
        self.assertIn("HTTP 403", str(ctx.exception))
        self.assertNotIn("secret-key", str(ctx.exception))

    def test_upload_evidence_bytes_uses_put_without_edge_headers(self) -> None:
        captured = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b""

        def fake_urlopen(request, timeout):
            captured["method"] = request.method
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["data"] = request.data
            return Response()

        client = EdgeApiClient("http://api:8000/api/v1", "client-123", "secret-key", opener=fake_urlopen)
        result = client.upload_evidence_bytes({"upload_url": "https://upload.local/file"}, b"frame-bytes")
        self.assertEqual(result["status"], "uploaded")
        self.assertEqual(captured["method"], "PUT")
        self.assertEqual(captured["url"], "https://upload.local/file")
        self.assertEqual(captured["data"], b"frame-bytes")
        header_names = {name.lower() for name in captured["headers"]}
        self.assertNotIn("x-edge-api-key", header_names)
        self.assertNotIn("x-edge-client-id", header_names)
        self.assertNotIn("x-request-id", header_names)


if __name__ == "__main__":
    unittest.main()
