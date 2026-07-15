import unittest
from datetime import datetime, timedelta, timezone
from typing import cast

from vigia_api.services.edge_workers import EdgeWorkerService
from vigia_api.api.v1 import edge_workers as edge_workers_api


class EdgeWorkersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = EdgeWorkerService()
        self.worker, self.api_key = self.service.register_worker("org-1", "site-a", "Lobby Cam Worker", ["cam-1", "cam-2"])

    def test_register_keeps_api_key_hash_only_and_returns_config(self) -> None:
        stored = self.service.repository.workers[self.worker.id]
        self.assertTrue(stored.api_key_hash)
        self.assertEqual(getattr(stored, "api_key", None), None)
        config = self.service.config(self.worker.client_id, self.api_key)
        worker_cfg = cast(dict[str, object], config["worker"])
        allowed = cast(list[str], config["allowed_camera_ids"])
        self.assertEqual(worker_cfg["organization_id"], "org-1")
        self.assertIn("cam-1", allowed)
        self.assertNotIn("api_key_hash", worker_cfg)
        self.assertNotIn("api_key", worker_cfg)

    def test_config_does_not_expose_sensitive_worker_fields(self) -> None:
        config = self.service.config(self.worker.client_id, self.api_key)
        worker_cfg = cast(dict[str, object], config["worker"])
        self.assertNotIn("api_key_hash", worker_cfg)
        self.assertNotIn("refresh_token", worker_cfg)

    def test_heartbeat_and_detection_create_incident(self) -> None:
        before = self.service.repository.workers[self.worker.id].last_heartbeat_at
        self.service.heartbeat(self.worker.client_id, self.api_key)
        after = self.service.repository.workers[self.worker.id].last_heartbeat_at
        self.assertIsNone(before)
        self.assertIsNotNone(after)

        result = self.service.submit_detection(
            self.worker.client_id,
            self.api_key,
            {
                "camera_id": "cam-1",
                "zone_id": "zone-1",
                "severity": "high",
                "timestamp": "2026-01-01T00:00:00Z",
                "event_type": "person_detected",
                "confidence": 0.91,
                "model_version": "v1.2.3",
                "evidence": {"image": "snapshot.jpg"},
            },
        )
        incident = cast(dict[str, object], result["incident"])
        self.assertEqual(incident["camera_id"], "cam-1")
        self.assertEqual(incident["organization_id"], "org-1")
        metadata = cast(dict[str, object], incident["metadata"])
        self.assertEqual(metadata["event_type"], "person_detected")
        self.assertEqual(metadata["model_version"], "v1.2.3")

    def test_retried_detection_event_is_idempotent(self) -> None:
        payload: dict[str, object] = {
            "event_id": "evt-retry-1",
            "camera_id": "cam-1",
            "zone_id": "zone-1",
            "severity": "high",
            "timestamp": "2026-01-01T00:00:00Z",
        }

        first = self.service.submit_detection(self.worker.client_id, self.api_key, payload)
        second = self.service.submit_detection(self.worker.client_id, self.api_key, payload)
        third = self.service.submit_detection(self.worker.client_id, self.api_key, {**payload, "event_id": "evt-retry-2"})

        first_incident = cast(dict[str, object], first["incident"])
        second_incident = cast(dict[str, object], second["incident"])
        third_incident = cast(dict[str, object], third["incident"])
        self.assertEqual(first_incident["id"], second_incident["id"])
        self.assertNotEqual(first_incident["id"], third_incident["id"])
        incidents = self.service.incident_repository.list_by_organization("org-1")
        self.assertEqual(len(incidents), 2)
        self.assertEqual(len(self.service.incident_repository.audit_logs("org-1", str(first_incident["id"]))), 1)

    def test_detection_rejects_cross_site_or_unauthorized_camera(self) -> None:
        with self.assertRaises(PermissionError):
            self.service.submit_detection(self.worker.client_id, self.api_key, {"camera_id": "cam-x", "zone_id": "zone-1", "severity": "low"})
        with self.assertRaises(PermissionError):
            self.service.submit_detection(self.worker.client_id, self.api_key, {"organization_id": "org-2", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "low"})

    def test_evidence_path_is_scoped_to_worker_org(self) -> None:
        result = self.service.request_evidence_upload(self.worker.client_id, self.api_key, "file-1")
        self.assertTrue(result["upload_path"].startswith("org/org-1/edge-workers/"))

    def test_revoke_blocks_future_calls(self) -> None:
        self.service.revoke(self.worker.id)
        with self.assertRaises(PermissionError):
            self.service.heartbeat(self.worker.client_id, self.api_key)
        with self.assertRaises(PermissionError):
            self.service.request_evidence_upload(self.worker.client_id, self.api_key, "file-2")

    def test_offline_worker_detection_uses_heartbeat_threshold(self) -> None:
        self.assertTrue(self.service.is_offline(self.worker.id, threshold_seconds=60, now=datetime.now(timezone.utc)))
        self.service.heartbeat(self.worker.client_id, self.api_key)
        self.assertFalse(self.service.is_offline(self.worker.id, threshold_seconds=60, now=datetime.now(timezone.utc)))
        self.service.repository.workers[self.worker.id].last_heartbeat_at = datetime.now(timezone.utc) - timedelta(seconds=120)
        self.assertTrue(self.service.is_offline(self.worker.id, threshold_seconds=60, now=datetime.now(timezone.utc)))

    def test_register_route_requires_org_permission_and_uses_path_org(self) -> None:
        class Membership:
            role = "manager"

        class Request:
            app = type("App", (), {"state": type("State", (), {})()})()

        payload = edge_workers_api.EdgeWorkerCreateIn(organization_id="org-1", site_id="site-a", name="Demo", allowed_camera_ids=["cam-1"])
        result = edge_workers_api.register_worker("org-1", payload, request=Request(), membership=Membership())
        self.assertEqual(result["worker"]["organization_id"], "org-1")


if __name__ == "__main__":
    unittest.main()
