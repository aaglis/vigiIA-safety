import unittest
from datetime import datetime, timedelta, timezone

from vigia_api.domain.evidence import EvidenceKind, EvidenceSource
from vigia_api.domain.incidents import parse_detection_event
from vigia_api.services.edge_workers import EdgeWorkerService
from vigia_api.services.evidence import EvidenceService
from vigia_api.services.jobs import OperationalJobsService
from vigia_api.services.incidents import InMemoryIncidentRepository
from vigia_api.settings import Settings


class JobsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.incidents = InMemoryIncidentRepository()
        self.edge_workers = EdgeWorkerService(incident_repository=self.incidents)
        self.evidence = EvidenceService()
        self.jobs = OperationalJobsService(self.edge_workers, self.evidence, self.incidents)
        self.worker, self.api_key = self.edge_workers.register_worker("org-1", "site-a", "worker-1", ["cam-1"])

    def test_offline_workers_job_is_idempotent_and_tenant_scoped(self) -> None:
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.edge_workers.repository.workers[self.worker.id].last_heartbeat_at = now - timedelta(seconds=400)
        result = self.jobs.run_offline_workers(organization_id="org-1", threshold_seconds=300, now=now)
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["offline_workers"][0]["organization_id"], "org-1")
        self.assertNotIn("api_key_hash", result["offline_workers"][0])
        self.assertNotIn("client_id", result["offline_workers"][0])
        second = self.jobs.run_offline_workers(organization_id="org-1", threshold_seconds=300, now=now)
        self.assertEqual(second["count"], 1)

    def test_evidence_retention_job_supports_dry_run_and_purge(self) -> None:
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        evidence = self.evidence.register_evidence("org-1", "inc-1", "file-1", "image/jpeg", 1, "user-1", EvidenceSource.USER, EvidenceKind.SNAPSHOT)
        evidence.created_at = now - timedelta(days=40)
        dry_run = self.jobs.run_evidence_retention("org-1", confirm=False, now=now)
        self.assertTrue(dry_run["dry_run"])
        self.assertEqual(dry_run["count"], 1)
        purge = self.jobs.run_evidence_retention("org-1", confirm=True, actor_user_id="actor-1", reason="cleanup", now=now)
        self.assertFalse(purge["dry_run"])
        self.assertEqual(purge["count"], 1)
        self.assertIsNotNone(self.evidence.repository.evidence[("org-1", "inc-1", "file-1")].deleted_at)

    def test_notifications_job_processes_pending_attempts_once(self) -> None:
        event = parse_detection_event({"organization_id": "org-1", "event_id": "evt-1", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "high"})
        incident = self.incidents.create_from_detection(event)
        first = self.jobs.run_notifications("org-1", incident_id=incident.id, now=datetime(2026, 1, 1, tzinfo=timezone.utc))
        second = self.jobs.run_notifications("org-1", incident_id=incident.id, now=datetime(2026, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(first["count"], 1)
        self.assertEqual(second["count"], 0)
        self.assertEqual(self.incidents.notifications("org-1", incident.id)[0].status, "sent")

    def test_smtp_disabled_or_misconfigured_is_recorded_without_blocking_incident(self) -> None:
        disabled_settings = Settings(incident_notification_enabled=False)
        disabled_repo = InMemoryIncidentRepository(app_settings=disabled_settings)
        disabled_repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "critical"}))
        disabled_jobs = OperationalJobsService(self.edge_workers, self.evidence, disabled_repo, app_settings=disabled_settings)
        result = disabled_jobs.run_notifications("org-1")
        self.assertEqual(result["count"], 0)
        self.assertEqual(disabled_repo.list_notifications("org-1")[0].status, "suppressed")

        smtp_settings = Settings(
            incident_notification_mode="smtp",
            smtp_host="smtp.example.com",
            smtp_user="dev-only",
            smtp_password="dev-only",
            smtp_from="alerts@example.com",
        )
        smtp_repo = InMemoryIncidentRepository(app_settings=smtp_settings)
        incident = smtp_repo.create_from_detection(parse_detection_event({"organization_id": "org-1", "camera_id": "cam-1", "zone_id": "zone-1", "severity": "critical"}))
        smtp_jobs = OperationalJobsService(self.edge_workers, self.evidence, smtp_repo, app_settings=smtp_settings)
        smtp_jobs.run_notifications("org-1", incident_id=incident.id)
        self.assertEqual(smtp_repo.notifications("org-1", incident.id)[0].status, "failed")
        self.assertEqual(smtp_repo.notifications("org-1", incident.id)[0].payload["reason"], "smtp_misconfigured")


if __name__ == "__main__":
    unittest.main()
