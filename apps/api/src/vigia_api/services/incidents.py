from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from dataclasses import replace
from typing import Any

from ..domain.incidents import (
    AuditLogEntry,
    DetectionEvent,
    Incident,
    IncidentStatus,
    NotificationAttempt,
    new_id,
)
from ..observability import log_event
from ..settings import settings


SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _is_notifiable_severity(severity: str) -> bool:
    normalized = severity.strip().lower()
    threshold = settings.incident_notification_severity_threshold.strip().lower()
    return SEVERITY_ORDER.get(normalized, 0) >= SEVERITY_ORDER.get(threshold, 3)


class InMemoryIncidentRepository:
    def __init__(self, app_settings: Any | None = None) -> None:
        self._incidents: dict[str, Incident] = {}
        self._audit_logs: list[AuditLogEntry] = []
        self._notifications: list[NotificationAttempt] = []
        self.settings = app_settings or settings

    def create_from_detection(self, event: DetectionEvent) -> Incident:
        existing = self.get_by_detection_event(event.organization_id, event.event_id)
        if existing is not None:
            log_event("incident.detection_duplicate", organization_id=event.organization_id, incident_id=existing.id, detection_event_id=event.event_id)
            return existing
        incident = Incident(
            id=new_id(),
            organization_id=event.organization_id,
            site_id=event.site_id,
            detection_event_id=event.event_id,
            camera_id=event.camera_id,
            zone_id=event.zone_id,
            worker_id=event.worker_id,
            event_type=event.event_type,
            severity=event.severity,
            summary=event.summary,
            confidence=event.confidence,
            metadata={
                "event_type": event.event_type,
                "site_id": event.site_id,
                "worker_id": event.worker_id,
                "confidence": event.confidence,
                "model_version": event.model_version,
                "evidence": event.evidence,
                **event.metadata,
            },
            created_at=event.detected_at,
            updated_at=event.detected_at,
        )
        self._incidents[incident.id] = incident
        self._audit_logs.append(
            AuditLogEntry(
                id=new_id(),
                organization_id=incident.organization_id,
                incident_id=incident.id,
                action="created",
                from_status=None,
                to_status=incident.status.value,
                actor="system",
                created_at=datetime.now(timezone.utc),
                metadata={"detection_event_id": event.event_id},
            )
        )
        if _is_notifiable_severity(incident.severity):
            mode = self.settings.incident_notification_mode.strip().lower()
            enabled = bool(self.settings.incident_notification_enabled)
            status = "queued"
            channel = "mock" if mode != "smtp" else "email"
            payload = {"severity": incident.severity, "channel": channel, "mode": mode, "recipients": len(self.settings.incident_notification_recipients)}
            if not enabled:
                status = "suppressed"
                payload["reason"] = "disabled"
            elif mode == "smtp" and (self.settings.smtp_host.startswith("smtp.dev.local") or self.settings.smtp_user in {"dev-only", ""} or self.settings.smtp_password in {"dev-only", ""}):
                status = "failed"
                payload["reason"] = "smtp_misconfigured"
            self._notifications.append(NotificationAttempt(id=new_id(), organization_id=incident.organization_id, incident_id=incident.id, channel=channel, status=status, created_at=datetime.now(timezone.utc), payload=payload))
            log_event("incident.notification_attempt", organization_id=incident.organization_id, incident_id=incident.id, channel=channel, status=status, severity=incident.severity, recipients=len(self.settings.incident_notification_recipients))
        log_event("incident.created", organization_id=incident.organization_id, incident_id=incident.id, edge_worker_id=str(incident.worker_id) if incident.worker_id else None, severity=incident.severity, camera_id=incident.camera_id)
        return incident

    def get_by_detection_event(self, organization_id: str, detection_event_id: str) -> Incident | None:
        return next((i for i in self._incidents.values() if i.organization_id == organization_id and i.detection_event_id == detection_event_id), None)

    def list_by_organization(self, organization_id: str) -> list[Incident]:
        return [i for i in self._incidents.values() if i.organization_id == organization_id]

    def list_filtered(self, organization_id: str, **filters) -> list[Incident]:
        items = self.list_by_organization(organization_id)
        status = filters.get("status")
        site_id = filters.get("site_id")
        camera_id = filters.get("camera_id")
        zone_id = filters.get("zone_id")
        severity = filters.get("severity")
        created_from = filters.get("created_from")
        created_to = filters.get("created_to")
        if status:
            items = [i for i in items if i.status.value == status]
        if site_id:
            items = [i for i in items if i.site_id == site_id]
        if camera_id:
            items = [i for i in items if i.camera_id == camera_id]
        if zone_id:
            items = [i for i in items if i.zone_id == zone_id]
        if severity:
            items = [i for i in items if i.severity == severity]
        if created_from:
            items = [i for i in items if i.created_at >= created_from]
        if created_to:
            items = [i for i in items if i.created_at <= created_to]
        return items

    def get(self, organization_id: str, incident_id: str) -> Incident:
        incident = self._incidents[incident_id]
        if incident.organization_id != organization_id:
            raise KeyError(incident_id)
        return incident

    def transition(self, organization_id: str, incident_id: str, status: IncidentStatus, actor: str, reason: str | None = None) -> Incident:
        incident = self.get(organization_id, incident_id)
        previous = incident.status
        allowed: dict[IncidentStatus, set[IncidentStatus]] = {
            IncidentStatus.OPEN: {IncidentStatus.ACKNOWLEDGED, IncidentStatus.RESOLVED, IncidentStatus.DISMISSED},
            IncidentStatus.ACKNOWLEDGED: {IncidentStatus.RESOLVED, IncidentStatus.DISMISSED},
            IncidentStatus.RESOLVED: set(),
            IncidentStatus.DISMISSED: set(),
        }
        if status not in allowed[previous]:
            raise ValueError(f"invalid transition from {previous.value} to {status.value}")
        if status in {IncidentStatus.RESOLVED, IncidentStatus.DISMISSED} and not (reason and reason.strip()):
            raise ValueError(f"{status.value} requires reason")
        incident.status = status
        incident.updated_at = datetime.now(timezone.utc)
        if status == IncidentStatus.ACKNOWLEDGED:
            incident.acknowledged_at = incident.updated_at
            incident.acknowledged_by = actor
        elif status == IncidentStatus.RESOLVED:
            incident.resolved_at = incident.updated_at
            incident.resolved_by = actor
            incident.resolution_reason = reason.strip() if reason else None
        elif status == IncidentStatus.DISMISSED:
            incident.dismissed_at = incident.updated_at
            incident.dismissed_by = actor
            incident.dismiss_reason = reason.strip() if reason else None
        self._audit_logs.append(
            AuditLogEntry(
                id=new_id(),
                organization_id=organization_id,
                incident_id=incident_id,
                action=f"incident.{status.value}",
                from_status=previous.value,
                to_status=status.value,
                actor=actor,
                created_at=incident.updated_at,
                metadata={"previous_status": previous.value, "next_status": status.value, "actor": actor, **({"reason": reason.strip()} if reason and reason.strip() else {})},
            )
        )
        log_event("incident.transition", organization_id=organization_id, incident_id=incident_id, status=status.value, actor=actor)
        return incident

    def audit_logs(self, organization_id: str, incident_id: str) -> list[AuditLogEntry]:
        return [entry for entry in self._audit_logs if entry.organization_id == organization_id and entry.incident_id == incident_id]

    def notifications(self, organization_id: str, incident_id: str) -> list[NotificationAttempt]:
        return [entry for entry in self._notifications if entry.organization_id == organization_id and entry.incident_id == incident_id]

    def list_notifications(self, organization_id: str, status: str | None = None) -> list[NotificationAttempt]:
        items = [entry for entry in self._notifications if entry.organization_id == organization_id]
        if status is not None:
            items = [entry for entry in items if entry.status == status]
        return items

    def update_notification_status(self, notification_id: str, status: str, *, processed_at: datetime | None = None, error: str | None = None) -> NotificationAttempt:
        for index, entry in enumerate(self._notifications):
            if entry.id == notification_id:
                updated = replace(entry, status=status, payload={**entry.payload, **({"processed_at": processed_at.isoformat()} if processed_at else {}), **({"error": error} if error else {})})
                self._notifications[index] = updated
                return updated
        raise KeyError(notification_id)


def incident_to_dict(incident: Incident) -> dict[str, Any]:
    data = asdict(incident)
    data["status"] = incident.status.value
    return data
