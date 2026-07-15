import unittest
from typing import cast

from vigia_api.container import edge_worker_service, incident_repository
from vigia_api.domain.incidents import parse_detection_event


class IncidentStoreIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        edge_worker_service.repository.workers.clear()
        edge_worker_service.repository.workers_by_client_id.clear()
        edge_worker_service.repository.camera_catalog.clear()
        incident_repository._incidents.clear()
        incident_repository._audit_logs.clear()
        incident_repository._notifications.clear()

    def test_detection_flow_uses_shared_incident_store(self) -> None:
        worker, api_key = edge_worker_service.register_worker("org-1", "site-a", "worker", ["cam-1"])
        result = edge_worker_service.submit_detection(worker.client_id, api_key, {
            "camera_id": "cam-1",
            "zone_id": "zone-1",
            "severity": "high",
            "timestamp": "2026-01-01T00:00:00Z",
            "event_type": "person_detected",
            "confidence": 0.95,
            "model_version": "v1",
        })
        incident = cast(dict[str, object], result["incident"])
        items = incident_repository.list_by_organization("org-1")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, incident["id"])
        self.assertEqual(items[0].created_at.isoformat(), "2026-01-01T00:00:00+00:00")
        detailed = incident_repository.get("org-1", str(incident["id"]))
        self.assertEqual(detailed.camera_id, "cam-1")

    def test_api_and_edge_share_same_store_object(self) -> None:
        from vigia_api.api.v1 import incidents as incidents_api
        from vigia_api.api.v1 import edge_workers as edge_workers_api

        self.assertIs(incidents_api.incident_repository, edge_workers_api.service.incident_repository)
        self.assertIs(incidents_api.incident_repository, incident_repository)


if __name__ == "__main__":
    unittest.main()
