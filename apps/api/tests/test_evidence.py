import unittest
from datetime import datetime, timedelta, timezone
from typing import cast
import os

from vigia_api.domain.evidence import EvidenceKind, EvidencePurgeError, EvidenceSource
from vigia_api.services.evidence import EvidenceService, InMemoryEvidenceMetadataRepository
from vigia_api.services.evidence_storage import MockEvidenceStorage, default_evidence_storage
from vigia_api.services.edge_workers import EdgeWorkerService
from vigia_api.api.v1 import evidence as evidence_api
from vigia_api import settings as settings_module


class EvidenceTest(unittest.TestCase):
    def setUp(self) -> None:
        settings_module.settings.app_env = "dev"
        settings_module.settings.s3_endpoint_url = None
        self.service = EvidenceService()

    def test_metadata_object_key_and_private_bucket(self) -> None:
        evidence = self.service.register_evidence("org-1", "inc-1", "file-1", "image/jpeg", 1234, "user-1", EvidenceSource.USER, EvidenceKind.SNAPSHOT, {"uploaded_by": "camera"})
        self.assertEqual(evidence.object_key, "org/org-1/incidents/inc-1/evidence/file-1")
        self.assertEqual(evidence.media_type, "image/jpeg")
        self.assertEqual(evidence.metadata["uploaded_by"], "camera")
        self.assertFalse(self.service.repository.public_bucket)

    def test_signed_download_url_is_short_and_audited(self) -> None:
        self.service.register_evidence("org-1", "inc-1", "file-1", "image/jpeg", 1234, "user-1", EvidenceSource.USER)
        result = self.service.get_download_url("org-1", "inc-1", "file-1", "actor-1", permission_checked=True, ttl_seconds=123)
        self.assertTrue(cast(str, result["download_url"]).startswith("https://s3.mock/"))
        self.assertIn("method=GET", cast(str, result["download_url"]))
        self.assertIn("ttl=123", cast(str, result["download_url"]))
        self.assertGreater(datetime.fromisoformat(cast(str, result["expires_at"])), datetime.now(timezone.utc))
        self.assertEqual(len(self.service.repository.audit_logs), 1)
        self.assertEqual(self.service.repository.audit_logs[0].action, "evidence.download")
        self.assertNotIn("download_url", self.service.repository.audit_logs[0].metadata)

    def test_upload_url_uses_storage_adapter_and_metadata_repo(self) -> None:
        storage = MockEvidenceStorage(bucket_name="evidence-bucket")
        service = EvidenceService(storage=storage)
        result = service.request_upload_url("org-1", "inc-1", "file-1", "actor-1", ttl_seconds=321)
        self.assertTrue(cast(str, result["upload_url"]).startswith("https://s3.mock/"))
        self.assertIn("method=PUT", cast(str, result["upload_url"]))
        self.assertIn("ttl=321", cast(str, result["upload_url"]))
        self.assertGreater(datetime.fromisoformat(cast(str, result["expires_at"])), datetime.now(timezone.utc))
        saved_repo = cast(InMemoryEvidenceMetadataRepository, service.metadata_repository)
        saved = saved_repo.get("org-1", "inc-1", "file-1")
        self.assertIsNotNone(saved)
        self.assertEqual(cast(dict[str, object], saved)["object_key"], "org/org-1/incidents/inc-1/evidence/file-1")
        self.assertNotIn("upload_url", service.repository.audit_logs[-1].metadata)

    def test_cross_tenant_access_is_denied(self) -> None:
        self.service.register_evidence("org-1", "inc-1", "file-1", "image/jpeg", 1234, "user-1", EvidenceSource.USER)
        with self.assertRaises(KeyError):
            self.service.get_download_url("org-2", "inc-1", "file-1", "actor-1")

    def test_retention_policy_default_and_override(self) -> None:
        default_policy = self.service.get_retention_policy("org-1")
        self.assertEqual(default_policy.snapshot_days, 30)
        updated = self.service.set_retention_policy("org-1", metadata_days=90, snapshot_days=15)
        self.assertEqual(updated.metadata_days, 90)
        self.assertEqual(self.service.get_retention_policy("org-1").snapshot_days, 15)

    def test_edge_worker_other_org_cannot_request_upload_for_foreign_org(self) -> None:
        edge_service = EdgeWorkerService()
        worker, api_key = edge_service.register_worker("org-1", "site-a", "worker", ["cam-1"])
        upload = cast(dict[str, str], edge_service.request_evidence_upload(worker.client_id, api_key, "file-1", "inc-1"))
        upload_path = str(upload["upload_path"])
        self.assertTrue(upload_path.startswith("org/org-1/incidents/inc-1/evidence/"))
        with self.assertRaises(PermissionError):
            self.service.worker_can_request_upload("org-2", "org-1")

    def test_upload_url_is_audited(self) -> None:
        self.service.request_upload_url("org-1", "inc-1", "file-1", "actor-1")
        self.assertEqual(self.service.repository.audit_logs[-1].action, "evidence.upload_url")

    def test_retention_update_is_audited(self) -> None:
        self.service.set_retention_policy("org-1", snapshot_days=7, actor_user_id="actor-1", reason="contract")
        self.assertEqual(self.service.repository.audit_logs[-1].action, "retention.update")
        self.assertEqual(self.service.repository.audit_logs[-1].metadata["reason"], "contract")

    def test_route_ignores_actor_spoofing(self) -> None:
        class CurrentUser:
            def __init__(self) -> None:
                self.user = type("U", (), {"id": "real-user"})()

        class Request:
            method = "PUT"
            headers = {"origin": "http://localhost:3000"}
            client = type("Client", (), {"host": "testclient"})()
            url = type("Url", (), {"path": "/api/v1/organizations/org-1/evidence/retention"})()

        payload = evidence_api.EvidenceRetentionIn(snapshot_days=5, actor_user_id="spoofed", reason="policy")
        result = evidence_api.update_retention_policy("org-1", payload, request=Request(), current_user=CurrentUser())
        self.assertEqual(result["snapshot_days"], 5)
        self.assertEqual(evidence_api.service.repository.audit_logs[-1].actor_user_id, "real-user")

    def test_preview_and_purge_respect_retention_and_tenant(self) -> None:
        old = datetime.now(timezone.utc) - timedelta(days=40)
        fresh = datetime.now(timezone.utc) - timedelta(days=1)
        expired = self.service.register_evidence("org-1", "inc-old", "file-old", "image/jpeg", 1, "user-1", EvidenceSource.USER, EvidenceKind.SNAPSHOT)
        expired.created_at = old
        fresh_evidence = self.service.register_evidence("org-1", "inc-new", "file-new", "image/jpeg", 1, "user-1", EvidenceSource.USER, EvidenceKind.SNAPSHOT)
        fresh_evidence.created_at = fresh
        other = self.service.register_evidence("org-2", "inc-other", "file-other", "image/jpeg", 1, "user-2", EvidenceSource.USER, EvidenceKind.SNAPSHOT)
        other.created_at = old
        self.service.set_retention_policy("org-1", snapshot_days=30)
        self.service.set_retention_policy("org-2", snapshot_days=30)

        preview = self.service.preview_expired_evidence("org-1", now=datetime.now(timezone.utc))
        self.assertEqual(len(preview), 1)
        self.assertEqual(preview[0]["file_id"], "file-old")
        self.assertEqual(preview[0]["organization_id"], "org-1")

        with self.assertRaises(EvidencePurgeError):
            self.service.purge_expired_evidence("org-1", confirm=False)

        result = self.service.purge_expired_evidence("org-1", confirm=True, actor_user_id="actor-1", reason="cleanup", now=datetime.now(timezone.utc))
        self.assertEqual(result["count"], 1)
        self.assertIsNotNone(self.service.repository.evidence[("org-1", "inc-old", "file-old")].deleted_at)
        self.assertIsNone(self.service.repository.evidence[("org-1", "inc-new", "file-new")].deleted_at)
        self.assertIsNone(self.service.repository.evidence[("org-2", "inc-other", "file-other")].deleted_at)
        self.assertEqual(self.service.repository.audit_logs[-1].action, "purge.confirm")

    def test_private_bucket_validation_uses_storage_adapter(self) -> None:
        service = EvidenceService(storage=MockEvidenceStorage(bucket_name="evidence-bucket", public_bucket=True))
        with self.assertRaises(ValueError):
            service.request_upload_url("org-1", "inc-1", "file-1", "actor-1")

    def test_staging_requires_real_storage_endpoint(self) -> None:
        prev = os.environ.copy()
        try:
            os.environ["APP_ENV"] = "staging"
            from vigia_api import settings as settings_module
            settings_module.settings.app_env = "staging"
            settings_module.settings.s3_endpoint_url = None
            with self.assertRaises(RuntimeError):
                default_evidence_storage()
        finally:
            os.environ.clear(); os.environ.update(prev)

    def test_list_evidence_and_audit_logs_support_pagination(self) -> None:
        self.service.register_evidence("org-1", "inc-1", "file-1", "image/jpeg", 1, "user-1", EvidenceSource.USER)
        self.service.register_evidence("org-1", "inc-2", "file-2", "image/jpeg", 1, "user-1", EvidenceSource.USER)
        self.service.request_upload_url("org-1", "inc-3", "file-3", "actor-1")
        items = self.service.list_evidence("org-1", limit=1, offset=0)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].organization_id, "org-1")
        logs = self.service.list_audit_logs("org-1", limit=1, offset=0)
        self.assertGreaterEqual(len(logs), 1)


if __name__ == "__main__":
    unittest.main()
