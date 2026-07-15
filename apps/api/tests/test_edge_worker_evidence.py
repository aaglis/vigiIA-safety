import unittest
from typing import cast

from vigia_api.container import build_container
from vigia_api.domain.edge_workers import EdgeWorker
from vigia_api.domain.evidence import EvidenceSource
from vigia_api.domain.incidents import parse_detection_event
from vigia_api.services.security import hash_token


class EdgeWorkerEvidenceTest(unittest.TestCase):
    def test_detection_registers_tenant_scoped_edge_evidence(self) -> None:
        container = build_container(repository_backend="memory", seed_dev=False)
        worker = EdgeWorker(id="worker-1", organization_id="org-1", site_id="site-1", name="Worker", client_id="client-1", api_key_hash=hash_token("key-1"), allowed_camera_ids=["cam-1"])
        container.edge_worker_service.repository.save(worker)
        container.edge_worker_service.camera_catalog[("org-1", "site-1")] = {"cam-1"}
        container.edge_worker_service.evidence_service = container.evidence_service
        result = container.edge_worker_service.submit_detection("client-1", "key-1", {"organization_id": "org-1", "site_id": "site-1", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "high", "event_id": "evt-2", "evidence": {"file_id": "file-2", "upload_path": "org/org-1/edge-workers/worker-1/evidence/file-2", "size": 10, "sha256_hex": "def", "frame_timestamp": "2026-01-01T00:00:00Z", "source_type": "image"}, "metadata": {"cv_mode": "real"}})
        result = cast(dict[str, object], result)
        self.assertEqual(result["worker_id"], "worker-1")
        incident = cast(dict[str, object], result["incident"])
        evidence = container.evidence_service.list_evidence("org-1", incident_id=str(incident["id"]), limit=None)
        self.assertTrue(evidence)
        self.assertEqual(evidence[0].source, EvidenceSource.EDGE_WORKER)
        self.assertEqual(evidence[0].metadata["upload_path"], "org/org-1/edge-workers/worker-1/evidence/file-2")


if __name__ == "__main__":
    unittest.main()
