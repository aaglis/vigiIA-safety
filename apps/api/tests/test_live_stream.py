import unittest
from dataclasses import dataclass
from urllib.parse import urlparse

from vigia_api.services.live_stream import LiveStreamService, LiveStreamUnavailable, stream_path_for


@dataclass
class FakeCamera:
    id: str
    stream_identifier: str


class FakeOperationsRepository:
    def __init__(self, cameras):
        self._cameras = cameras

    def list_cameras(self, organization_id):
        return self._cameras


class FakeEdgeWorkerService:
    """Aceita só a credencial do worker demo, que enxerga apenas camera-demo-01."""

    def config(self, client_id, api_key):
        if (client_id, api_key) != ("worker-1", "secret-1"):
            raise PermissionError("invalid credentials")
        return {"cameras": [{"id": "cam-1", "stream_identifier": "rtsp://edge:8554/patio-1"}]}


class FakeSettings:
    jwt_secret = "test-secret"
    live_stream_public_base_url = "http://edge.local:8889"
    live_stream_ticket_ttl_seconds = 60


def build_service(ttl=60):
    settings = FakeSettings()
    settings.live_stream_ticket_ttl_seconds = ttl
    cameras = [FakeCamera(id="cam-1", stream_identifier="rtsp://edge:8554/patio-1"), FakeCamera(id="cam-file", stream_identifier="/assets/sample.mp4")]
    return LiveStreamService(operations_repository=FakeOperationsRepository(cameras), settings=settings, edge_worker_service=FakeEdgeWorkerService())


def token_of(url):
    return dict(part.split("=", 1) for part in urlparse(url).query.split("&"))["token"]


class StreamPathTest(unittest.TestCase):
    def test_extracts_path_from_rtsp_url(self):
        self.assertEqual(stream_path_for("rtsp://edge:8554/patio-1"), "patio-1")

    def test_file_source_has_no_live_stream(self):
        with self.assertRaises(LiveStreamUnavailable):
            stream_path_for("/assets/sample.mp4")

    def test_rtsp_without_path_is_rejected(self):
        with self.assertRaises(LiveStreamUnavailable):
            stream_path_for("rtsp://edge:8554")


class LiveTicketTest(unittest.TestCase):
    def test_issues_whep_url_for_live_camera(self):
        ticket = build_service().issue_ticket("org-1", "cam-1")
        self.assertTrue(ticket.whep_url.startswith("http://edge.local:8889/patio-1/whep?token="))

    def test_camera_registered_as_file_has_no_ticket(self):
        with self.assertRaises(LiveStreamUnavailable):
            build_service().issue_ticket("org-1", "cam-file")

    def test_unknown_camera_raises(self):
        with self.assertRaises(KeyError):
            build_service().issue_ticket("org-1", "cam-404")


class AuthorizeTest(unittest.TestCase):
    def setUp(self):
        self.service = build_service()
        self.token = token_of(self.service.issue_ticket("org-1", "cam-1").whep_url)

    def test_valid_ticket_allows_read(self):
        self.assertTrue(self.service.authorize("patio-1", f"token={self.token}", "read"))

    def test_ticket_does_not_open_another_camera(self):
        self.assertFalse(self.service.authorize("outra-camera", f"token={self.token}", "read"))

    def test_missing_token_denies(self):
        self.assertFalse(self.service.authorize("patio-1", "", "read"))

    def test_tampered_token_denies(self):
        self.assertFalse(self.service.authorize("patio-1", f"token={self.token[:-4]}AAAA", "read"))

    def test_expired_ticket_denies(self):
        service = build_service(ttl=-1)
        token = token_of(service.issue_ticket("org-1", "cam-1").whep_url)
        self.assertFalse(service.authorize("patio-1", f"token={token}", "read"))

    def test_read_ticket_never_allows_publish(self):
        self.assertFalse(self.service.authorize("patio-1", f"token={self.token}", "publish"))

    def test_worker_credentials_allow_reading_its_own_camera(self):
        self.assertTrue(self.service.authorize("patio-1", "", "read", "worker-1", "secret-1"))

    def test_wrong_worker_credentials_deny(self):
        self.assertFalse(self.service.authorize("patio-1", "", "read", "worker-1", "senha-errada"))

    def test_worker_cannot_read_camera_outside_its_scope(self):
        self.assertFalse(self.service.authorize("camera-de-outro-cliente", "", "read", "worker-1", "secret-1"))


if __name__ == "__main__":
    unittest.main()
