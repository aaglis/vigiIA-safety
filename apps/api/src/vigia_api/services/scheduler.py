from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol, cast

from ..observability import log_event
from ..settings import Settings, settings
from .jobs import OperationalJobsService


class LockBackend(Protocol):
    def acquire(self, key: str, ttl_seconds: int) -> str | None: ...
    def release(self, key: str, token: str) -> bool: ...


class RedisLockBackend:
    def __init__(self, redis_client: Any) -> None:
        self.redis = redis_client
        self._release_script = None

    def acquire(self, key: str, ttl_seconds: int) -> str | None:
        token = uuid.uuid4().hex
        ok = self.redis.set(key, token, nx=True, ex=ttl_seconds)
        return token if ok else None

    def release(self, key: str, token: str) -> bool:
        script = self.redis.register_script(
            """
            if redis.call('GET', KEYS[1]) == ARGV[1] then
              return redis.call('DEL', KEYS[1])
            end
            return 0
            """
        )
        return bool(script(keys=[key], args=[token]))


class NullLockBackend:
    def acquire(self, key: str, ttl_seconds: int) -> str | None:
        return None

    def release(self, key: str, token: str) -> bool:
        return False


@dataclass
class SchedulerResult:
    ran: list[str]
    skipped: list[str]
    failed: list[str]


class JobScheduler:
    def __init__(self, jobs: Any, lock_backend: LockBackend | None = None, app_settings: Settings | None = None, platform_admin_service: Any | None = None) -> None:
        self.jobs = jobs
        self.settings = app_settings or settings
        self.lock_backend = lock_backend or NullLockBackend()
        self.platform_admin_service = platform_admin_service

    def _orgs(self) -> list[str]:
        explicit = [org.strip() for org in getattr(self.settings, "scheduler_organization_ids", []) if org and org.strip()]
        if explicit:
            return sorted(set(explicit))
        orgs: set[str] = set()
        edge_worker_service = getattr(self.jobs, "edge_worker_service", None)
        if edge_worker_service is not None and hasattr(edge_worker_service, "repository") and hasattr(edge_worker_service.repository, "list_all"):
            orgs.update(worker.organization_id for worker in edge_worker_service.repository.list_all())
        platform = self.platform_admin_service
        if platform is not None and hasattr(platform, "repository") and hasattr(platform.repository, "list_all"):
            orgs.update(org.id for org in platform.repository.list_all())
        incident_repo = getattr(self.jobs, "incident_repository", None)
        if incident_repo is not None:
            incidents = getattr(incident_repo, "list_notification_organizations", None)
            if callable(incidents):
                orgs.update(cast(list[str], incidents(status="queued")))
        return sorted(orgs)

    def _run_locked(self, key: str, action) -> tuple[bool, Any | None]:
        token = self.lock_backend.acquire(key, self.settings.scheduler_lock_ttl_seconds)
        if token is None:
            return False, None
        try:
            return True, action()
        finally:
            self.lock_backend.release(key, token)

    def _record_locked_job(self, result: SchedulerResult, job: str, organization_id: str | None, action: Callable[[], Any]) -> None:
        org_label = organization_id or "all"
        try:
            ran, payload = self._run_locked(f"scheduler:{job}:{org_label}", action)
            if not ran:
                result.skipped.append(f"{job}:{org_label}")
                log_event("scheduler.job.skipped", job=job, organization_id=org_label, reason="lock_unavailable")
                return
            result.ran.append(f"{job}:{org_label}")
            payload_dict = cast(dict[str, Any], payload or {})
            log_event("scheduler.job.ran", job=job, organization_id=org_label, count=payload_dict.get("count", 0))
        except Exception as exc:
            result.failed.append(f"{job}:{org_label}")
            log_event("scheduler.job.failed", job=job, organization_id=org_label, error=str(exc))

    def run_once(
        self,
        now: datetime | None = None,
        organization_id: str | None = None,
        *,
        run_notifications: bool = True,
        run_offline_workers: bool = True,
        run_evidence_retention: bool = True,
    ) -> SchedulerResult:
        now = now or datetime.now(timezone.utc)
        orgs = [organization_id] if organization_id else self._orgs()
        result = SchedulerResult(ran=[], skipped=[], failed=[])
        if run_notifications:
            for org in orgs:
                self._record_locked_job(result, "notifications", org, lambda org=org: self.jobs.run_notifications(org, now=now))

        if run_offline_workers:
            self._record_locked_job(result, "offline-workers", organization_id, lambda: self.jobs.run_offline_workers(organization_id=organization_id, now=now))

        if run_evidence_retention:
            for org in orgs:
                self._record_locked_job(
                    result,
                    "evidence-retention",
                    org,
                    lambda org=org: self.jobs.run_evidence_retention(
                        org,
                        confirm=self.settings.scheduler_evidence_retention_confirm,
                        actor_user_id="scheduler",
                        reason="scheduled_retention",
                        now=now,
                    ),
                )
        return result

    def run_forever(self, poll_seconds: int = 5, stop_after: int | None = None) -> None:
        cycles = 0
        last_run: dict[str, float] = {}
        while True:
            current = time.monotonic()
            if current - last_run.get("notifications", 0) >= self.settings.scheduler_notifications_interval_seconds:
                self.run_once(run_offline_workers=False, run_evidence_retention=False)
                last_run["notifications"] = current
            if current - last_run.get("offline-workers", 0) >= self.settings.scheduler_offline_workers_interval_seconds:
                self.run_once(run_notifications=False, run_evidence_retention=False)
                last_run["offline-workers"] = current
            if current - last_run.get("evidence-retention", 0) >= self.settings.scheduler_evidence_retention_interval_seconds:
                self.run_once(run_notifications=False, run_offline_workers=False)
                last_run["evidence-retention"] = current
            cycles += 1
            if stop_after is not None and cycles >= stop_after:
                return
            time.sleep(poll_seconds)
