import unittest
from dataclasses import dataclass

from vigia_api.services.scheduler import JobScheduler
from vigia_api.settings import Settings


@dataclass
class Attempt:
    id: str = "n-1"
    organization_id: str = "org-1"
    incident_id: str = "inc-1"
    channel: str = "email"
    status: str = "queued"


class FakeJobs:
    def __init__(self, incident_repository=None) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.incident_repository = incident_repository

    def run_notifications(self, organization_id: str, incident_id: str | None = None, now=None):
        self.calls.append(("notifications", organization_id))
        return {"count": 1, "notifications": [{"id": "n-1"}]}

    def run_offline_workers(self, organization_id: str | None = None, threshold_seconds: int = 300, now=None):
        self.calls.append(("offline-workers", organization_id))
        return {"count": 0, "offline_workers": []}

    def run_evidence_retention(self, organization_id: str, confirm: bool = False, actor_user_id: str | None = None, reason: str | None = None, now=None):
        self.calls.append(("evidence-retention", organization_id))
        return {"count": 0, "dry_run": not confirm, "expired": []}


class FakeLock:
    def __init__(self, acquire_result: str | None = "token") -> None:
        self.acquire_result = acquire_result
        self.acquired: list[str] = []

    def acquire(self, key: str, ttl_seconds: int) -> str | None:
        self.acquired.append(key)
        return self.acquire_result

    def release(self, key: str, token: str) -> bool:
        return True


class FakePlatformRepo:
    def list_all(self):
        return [type("Org", (), {"id": "org-1"})(), type("Org", (), {"id": "org-2"})()]


class FakePlatform:
    repository = FakePlatformRepo()


class FakeIncidentRepo:
    def list_notification_organizations(self, status: str | None = None):
        return ["org-queued"] if status == "queued" else []


class SchedulerTest(unittest.TestCase):
    def test_run_once_processes_all_jobs_and_uses_org_discovery(self) -> None:
        jobs = FakeJobs()
        scheduler = JobScheduler(jobs, lock_backend=FakeLock(), app_settings=Settings(scheduler_organization_ids=[]), platform_admin_service=FakePlatform())
        result = scheduler.run_once()
        self.assertEqual(jobs.calls, [
            ("notifications", "org-1"),
            ("notifications", "org-2"),
            ("offline-workers", None),
            ("evidence-retention", "org-1"),
            ("evidence-retention", "org-2"),
        ])
        self.assertEqual(result.failed, [])
        self.assertEqual(result.skipped, [])
        self.assertEqual(result.ran, [
            "notifications:org-1",
            "notifications:org-2",
            "offline-workers:all",
            "evidence-retention:org-1",
            "evidence-retention:org-2",
        ])

    def test_discovers_organizations_from_queued_notifications(self) -> None:
        jobs = FakeJobs(incident_repository=FakeIncidentRepo())
        scheduler = JobScheduler(jobs, lock_backend=FakeLock(), app_settings=Settings(scheduler_organization_ids=[]))
        result = scheduler.run_once(run_offline_workers=False, run_evidence_retention=False)
        self.assertEqual(jobs.calls, [("notifications", "org-queued")])
        self.assertEqual(result.ran, ["notifications:org-queued"])

    def test_lock_failure_skips_job_without_running(self) -> None:
        jobs = FakeJobs()
        scheduler = JobScheduler(jobs, lock_backend=FakeLock(acquire_result=None), app_settings=Settings(scheduler_organization_ids=["org-1"]))
        result = scheduler.run_once(organization_id="org-1")
        self.assertEqual(jobs.calls, [])
        self.assertEqual(result.skipped, ["notifications:org-1", "offline-workers:org-1", "evidence-retention:org-1"])

    def test_second_run_is_safe_with_locking(self) -> None:
        jobs = FakeJobs()
        lock = FakeLock()
        scheduler = JobScheduler(jobs, lock_backend=lock, app_settings=Settings(scheduler_organization_ids=["org-1"]))
        first = scheduler.run_once(organization_id="org-1")
        second = scheduler.run_once(organization_id="org-1")
        self.assertEqual(first.failed, [])
        self.assertEqual(second.failed, [])
        self.assertGreaterEqual(len(lock.acquired), 2)


if __name__ == "__main__":
    unittest.main()
