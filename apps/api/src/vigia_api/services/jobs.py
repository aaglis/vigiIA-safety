from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..observability import increment_metric, log_event
from ..settings import Settings, settings
from .edge_workers import EdgeWorkerService
from .evidence import EvidenceService
from .incidents import InMemoryIncidentRepository
from .notifications import NotificationSendError, Notifier, _sanitize_error, build_incident_email, build_notifier, is_resend_configured


def _worker_to_job_result(worker: Any) -> dict[str, Any]:
    return {
        "id": worker.id,
        "organization_id": worker.organization_id,
        "site_id": worker.site_id,
        "name": worker.name,
        "status": worker.status.value if hasattr(worker.status, "value") else str(worker.status),
        "last_heartbeat_at": worker.last_heartbeat_at.isoformat() if worker.last_heartbeat_at else None,
        "updated_at": worker.updated_at.isoformat() if worker.updated_at else None,
    }


class OperationalJobsService:
    def __init__(self, edge_worker_service: EdgeWorkerService, evidence_service: EvidenceService, incident_repository: Any, app_settings: Settings | None = None, notifier: Notifier | None = None) -> None:
        self.edge_worker_service = edge_worker_service
        self.evidence_service = evidence_service
        self.incident_repository = incident_repository
        self.settings = app_settings or settings
        self.notifier = notifier or build_notifier(self.settings)

    def _deliver(self, attempt: Any) -> tuple[str, str | None]:
        """Envia a notificação de fato. Falha de envio nunca derruba o job nem o incidente."""
        incident = self.incident_repository.get(attempt.organization_id, attempt.incident_id) if hasattr(self.incident_repository, "get") else None
        subject, body = build_incident_email(incident) if incident is not None else (f"[VigIA] Incidente {attempt.incident_id}", f"Incidente {attempt.incident_id}")
        try:
            self.notifier.send(subject=subject, body=body, recipients=list(self.settings.incident_notification_recipients))
            return "sent", None
        except NotificationSendError as exc:
            return "failed", str(exc)
        except Exception as exc:  # defensivo: qualquer erro inesperado vira falha registrada
            return "failed", _sanitize_error(exc, getattr(self.settings, "resend_api_key", None))

    def run_offline_workers(self, organization_id: str | None = None, threshold_seconds: int = 300, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        workers = self.edge_worker_service.repository.list_all()
        if organization_id is not None:
            workers = [worker for worker in workers if worker.organization_id == organization_id]
        offline = [worker for worker in workers if self.edge_worker_service.is_offline(worker.id, threshold_seconds=threshold_seconds, now=now)]
        result = {"organization_id": organization_id, "threshold_seconds": threshold_seconds, "now": now.isoformat(), "offline_workers": [_worker_to_job_result(worker) for worker in offline], "count": len(offline)}
        log_event("jobs.offline_workers", organization_id=organization_id, threshold_seconds=threshold_seconds, count=len(offline))
        increment_metric("worker_offline", ((organization_id or "all"), "job_run"))
        return result

    def run_evidence_retention(self, organization_id: str, confirm: bool = False, actor_user_id: str | None = None, reason: str | None = None, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        preview = self.evidence_service.preview_expired_evidence(organization_id, now=now)
        if not confirm:
            log_event("jobs.evidence_retention.dry_run", organization_id=organization_id, count=len(preview))
            return {"organization_id": organization_id, "dry_run": True, "count": len(preview), "expired": preview}
        result = self.evidence_service.purge_expired_evidence(organization_id, confirm=True, actor_user_id=actor_user_id, reason=reason, now=now)
        log_event("jobs.evidence_retention.purge", organization_id=organization_id, actor_user_id=actor_user_id or "system", count=result["count"], reason=reason)
        return {"organization_id": organization_id, "dry_run": False, **result}

    def run_notifications(self, organization_id: str, incident_id: str | None = None, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        repo = self.incident_repository
        if hasattr(repo, "list_notifications"):
            queued = [item for item in repo.list_notifications(organization_id, status="queued") if incident_id is None or item.incident_id == incident_id]
        else:
            queued = []
        processed: list[dict[str, Any]] = []
        for attempt in queued:
            next_status = "sent"
            error = None
            if attempt.channel == "email" and self.settings.incident_notification_mode.strip().lower() == "resend":
                if not self.settings.incident_notification_enabled:
                    next_status = "suppressed"
                    error = "disabled"
                elif not is_resend_configured(self.settings):
                    next_status = "failed"
                    error = "resend_misconfigured"
                else:
                    next_status, error = self._deliver(attempt)
            if hasattr(repo, "update_notification_status"):
                updated = repo.update_notification_status(attempt.id, next_status, processed_at=now, error=error)
            else:
                updated = attempt
            processed.append({"id": updated.id, "incident_id": updated.incident_id, "organization_id": updated.organization_id, "channel": updated.channel, "status": updated.status})
        log_event("jobs.notifications", organization_id=organization_id, incident_id=incident_id, count=len(processed), mode=self.settings.incident_notification_mode)
        return {"organization_id": organization_id, "incident_id": incident_id, "count": len(processed), "notifications": processed, "now": now.isoformat()}

    def run_all(self, organization_id: str | None = None, threshold_seconds: int = 300, confirm: bool = False, actor_user_id: str | None = None, reason: str | None = None, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(timezone.utc)
        result: dict[str, Any] = {"now": now.isoformat()}
        if organization_id is not None:
            result["offline_workers"] = self.run_offline_workers(organization_id=organization_id, threshold_seconds=threshold_seconds, now=now)
            result["evidence_retention"] = self.run_evidence_retention(organization_id=organization_id, confirm=confirm, actor_user_id=actor_user_id, reason=reason, now=now)
            result["notifications"] = self.run_notifications(organization_id=organization_id, now=now)
        else:
            orgs = sorted({worker.organization_id for worker in self.edge_worker_service.repository.list_all()})
            result["organizations"] = [self.run_all(organization_id=org, threshold_seconds=threshold_seconds, confirm=confirm, actor_user_id=actor_user_id, reason=reason, now=now) for org in orgs]
        return result
