from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, cast

try:
    from sqlalchemy import select  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    select = None  # type: ignore[assignment]

from ..domain.edge_workers import EdgeWorker, EdgeWorkerStatus
from ..domain.evidence import EvidenceAccessAuditLog
from ..domain.incidents import AuditLogEntry, DetectionEvent, Incident, IncidentStatus, NotificationAttempt, new_id
from ..services.notifications import is_resend_configured
from ..settings import settings as global_settings
from .models import EdgeWorker as EdgeWorkerRow
from .models import EvidenceAccessAuditLog as EvidenceAccessAuditLogRow
from .models import EvidenceMetadata as EvidenceMetadataRow
from .models import Incident as IncidentRow
from .models import NotificationAttempt as NotificationRow

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _is_notifiable_severity(severity: str, settings_obj: Any) -> bool:
    normalized = severity.strip().lower()
    threshold = settings_obj.incident_notification_severity_threshold.strip().lower()
    return SEVERITY_ORDER.get(normalized, 0) >= SEVERITY_ORDER.get(threshold, 3)


class SqlAlchemyIncidentRepository:
    def __init__(self, session_factory, app_settings: Any | None = None) -> None:
        self.session_factory = session_factory
        self.settings = app_settings or global_settings

    def _ensure_aware_utc(self, value: datetime | None, default_now: bool = False) -> datetime | None:
        if value is None:
            return datetime.now(timezone.utc) if default_now else None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def _to_domain(self, row: IncidentRow | None) -> Incident | None:
        if row is None:
            return None
        return Incident(
            id=row.id,
            organization_id=row.organization_id,
            site_id=row.site_id,
            detection_event_id=row.detection_event_id,
            camera_id=row.camera_id,
            zone_id=row.zone_id,
            worker_id=row.worker_id,
            event_type=row.event_type,
            severity=row.severity,
            summary=row.summary,
            confidence=row.confidence,
            metadata=json.loads(row.metadata_json or "{}"),
            status=IncidentStatus(row.status),
            created_at=cast(datetime, self._ensure_aware_utc(row.created_at, default_now=True)),
            updated_at=cast(datetime, self._ensure_aware_utc(row.updated_at, default_now=True)),
            acknowledged_at=self._ensure_aware_utc(getattr(row, "acknowledged_at", None)),
            acknowledged_by=getattr(row, "acknowledged_by", None),
            resolved_at=self._ensure_aware_utc(getattr(row, "resolved_at", None)),
            resolved_by=getattr(row, "resolved_by", None),
            resolution_reason=getattr(row, "resolution_reason", None),
            dismissed_at=self._ensure_aware_utc(getattr(row, "dismissed_at", None)),
            dismissed_by=getattr(row, "dismissed_by", None),
            dismiss_reason=getattr(row, "dismiss_reason", None),
        )

    def save(self, incident: Incident) -> None:
        if self.session_factory is None:
            raise RuntimeError("SQLAlchemy not available")
        with self.session_factory() as session:
            row = IncidentRow(
                id=incident.id,
                organization_id=incident.organization_id,
                site_id=incident.site_id,
                detection_event_id=incident.detection_event_id,
                camera_id=incident.camera_id,
                zone_id=incident.zone_id,
                worker_id=incident.worker_id,
                event_type=incident.event_type,
                severity=incident.severity,
                summary=incident.summary,
                confidence=incident.confidence,
                status=incident.status.value,
                acknowledged_at=incident.acknowledged_at,
                acknowledged_by=incident.acknowledged_by,
                resolved_at=incident.resolved_at,
                resolved_by=incident.resolved_by,
                resolution_reason=incident.resolution_reason,
                dismissed_at=incident.dismissed_at,
                dismissed_by=incident.dismissed_by,
                dismiss_reason=incident.dismiss_reason,
                metadata_json=json.dumps(incident.metadata),
                created_at=incident.created_at,
                updated_at=incident.updated_at,
            )
            session.merge(row)
            session.commit()

    def create_from_detection(self, event: DetectionEvent) -> Incident:
        existing = self.get_by_detection_event(event.organization_id, event.event_id)
        if existing is not None:
            from ..observability import log_event
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
            metadata={"event_type": event.event_type, "site_id": event.site_id, "worker_id": event.worker_id, "confidence": event.confidence, "model_version": event.model_version, "evidence": event.evidence, **event.metadata},
            created_at=event.detected_at,
            updated_at=event.detected_at,
        )
        self.save(incident)
        self._append_audit_log(incident.organization_id, incident.id, "created", None, incident.status.value, "system", incident.created_at, {"detection_event_id": event.event_id})
        self._enqueue_notification(incident)
        return incident

    def _enqueue_notification(self, incident: Incident) -> None:
        if not _is_notifiable_severity(incident.severity, self.settings):
            return
        from ..observability import log_event

        mode = self.settings.incident_notification_mode.strip().lower()
        enabled = bool(self.settings.incident_notification_enabled)
        status = "queued"
        channel = "email" if mode == "resend" else "mock"
        payload: dict[str, Any] = {"severity": incident.severity, "channel": channel, "mode": mode, "recipients": len(self.settings.incident_notification_recipients)}
        if not enabled:
            status = "suppressed"
            payload["reason"] = "disabled"
        elif mode == "resend" and not is_resend_configured(self.settings):
            status = "failed"
            payload["reason"] = "resend_misconfigured"
        with self.session_factory() as session:
            session.add(NotificationRow(id=new_id(), organization_id=incident.organization_id, incident_id=incident.id, channel=channel, status=status, payload_json=json.dumps(payload), created_at=datetime.now(timezone.utc)))
            session.commit()
        log_event("incident.notification_attempt", organization_id=incident.organization_id, incident_id=incident.id, channel=channel, status=status, severity=incident.severity, recipients=len(self.settings.incident_notification_recipients))

    def _notification_to_domain(self, row: NotificationRow) -> NotificationAttempt:
        payload = json.loads(row.payload_json or "{}")
        if row.processed_at is not None:
            payload = {**payload, "processed_at": self._ensure_aware_utc(row.processed_at).isoformat()}
        return NotificationAttempt(id=row.id, organization_id=row.organization_id, incident_id=row.incident_id, channel=row.channel, status=row.status, created_at=self._ensure_aware_utc(row.created_at, default_now=True), payload=payload)

    def notifications(self, organization_id: str, incident_id: str) -> list[NotificationAttempt]:
        if self.session_factory is None or select is None:
            return []
        with self.session_factory() as session:
            rows = session.execute(select(NotificationRow).where(NotificationRow.organization_id == organization_id, NotificationRow.incident_id == incident_id)).scalars().all()
            return [self._notification_to_domain(row) for row in rows]

    def list_notifications(self, organization_id: str, status: str | None = None) -> list[NotificationAttempt]:
        if self.session_factory is None or select is None:
            return []
        with self.session_factory() as session:
            stmt = select(NotificationRow).where(NotificationRow.organization_id == organization_id)
            if status is not None:
                stmt = stmt.where(NotificationRow.status == status)
            return [self._notification_to_domain(row) for row in session.execute(stmt).scalars().all()]

    def update_notification_status(self, notification_id: str, status: str, *, processed_at: datetime | None = None, error: str | None = None) -> NotificationAttempt:
        with self.session_factory() as session:
            row = session.get(NotificationRow, notification_id)
            if row is None:
                raise KeyError(notification_id)
            row.status = status
            row.processed_at = processed_at or datetime.now(timezone.utc)
            if error is not None:
                payload = json.loads(row.payload_json or "{}")
                payload["error"] = error
                payload.setdefault("reason", error)
                row.payload_json = json.dumps(payload)
            session.commit()
            session.refresh(row)
            return self._notification_to_domain(row)

    def get_by_detection_event(self, organization_id: str, detection_event_id: str) -> Incident | None:
        if self.session_factory is None or select is None:
            return None
        with self.session_factory() as session:
            row = session.execute(select(IncidentRow).where(IncidentRow.organization_id == organization_id, IncidentRow.detection_event_id == detection_event_id)).scalar_one_or_none()
            return self._to_domain(row)

    def get(self, organization_id: str, incident_id: str) -> Incident | None:
        if self.session_factory is None or select is None:
            return None
        with self.session_factory() as session:
            row = session.get(IncidentRow, incident_id)
            if row is None or row.organization_id != organization_id:
                return None
            return self._to_domain(row)

    def list_by_organization(self, organization_id: str) -> list[Incident]:
        if self.session_factory is None or select is None:
            return []
        with self.session_factory() as session:
            items: list[Incident] = []
            for row in session.execute(select(IncidentRow).where(IncidentRow.organization_id == organization_id)).scalars().all():
                incident = self._to_domain(row)
                if incident is not None:
                    items.append(incident)
            return items

    def list_filtered(self, organization_id: str, **filters) -> list[Incident]:
        if self.session_factory is None or select is None:
            return []
        stmt = select(IncidentRow).where(IncidentRow.organization_id == organization_id)
        if filters.get("status"):
            stmt = stmt.where(IncidentRow.status == filters["status"])
        if filters.get("site_id"):
            stmt = stmt.where(IncidentRow.site_id == filters["site_id"])
        if filters.get("camera_id"):
            stmt = stmt.where(IncidentRow.camera_id == filters["camera_id"])
        if filters.get("zone_id"):
            stmt = stmt.where(IncidentRow.zone_id == filters["zone_id"])
        if filters.get("severity"):
            stmt = stmt.where(IncidentRow.severity == filters["severity"])
        if filters.get("created_from"):
            stmt = stmt.where(IncidentRow.created_at >= filters["created_from"])
        if filters.get("created_to"):
            stmt = stmt.where(IncidentRow.created_at <= filters["created_to"])
        with self.session_factory() as session:
            items: list[Incident] = []
            for row in session.execute(stmt).scalars().all():
                incident = self._to_domain(row)
                if incident is not None:
                    items.append(incident)
            return items

    def _append_audit_log(self, organization_id: str, incident_id: str, action: str, from_status: str | None, to_status: str, actor: str, created_at: datetime, metadata: dict[str, Any]) -> None:
        if self.session_factory is None:
            return
        from .models import IncidentAuditLog as IncidentAuditLogRow
        with self.session_factory() as session:
            session.add(IncidentAuditLogRow(id=new_id(), organization_id=organization_id, incident_id=incident_id, action=action, from_status=from_status, to_status=to_status, actor=actor, created_at=created_at, metadata_json=json.dumps(metadata)))
            session.commit()

    def transition(self, organization_id: str, incident_id: str, status: IncidentStatus, actor: str, reason: str | None = None) -> Incident:
        incident = self.get(organization_id, incident_id)
        if incident is None:
            raise KeyError(incident_id)
        previous = incident.status
        allowed = {
            IncidentStatus.OPEN: {IncidentStatus.ACKNOWLEDGED, IncidentStatus.RESOLVED, IncidentStatus.DISMISSED},
            IncidentStatus.ACKNOWLEDGED: {IncidentStatus.RESOLVED, IncidentStatus.DISMISSED},
            IncidentStatus.RESOLVED: set(),
            IncidentStatus.DISMISSED: set(),
        }
        if status not in allowed[previous]:
            raise ValueError(f"invalid transition from {previous.value} to {status.value}")
        if status in {IncidentStatus.RESOLVED, IncidentStatus.DISMISSED} and not (reason and reason.strip()):
            raise ValueError(f"{status.value} requires reason")
        now = datetime.now(timezone.utc)
        incident.status = status
        incident.updated_at = now
        if status == IncidentStatus.ACKNOWLEDGED:
            incident.acknowledged_at = now
            incident.acknowledged_by = actor
        elif status == IncidentStatus.RESOLVED:
            incident.resolved_at = now
            incident.resolved_by = actor
            incident.resolution_reason = reason.strip() if reason else None
        elif status == IncidentStatus.DISMISSED:
            incident.dismissed_at = now
            incident.dismissed_by = actor
            incident.dismiss_reason = reason.strip() if reason else None
        self.save(incident)
        meta = {"previous_status": previous.value, "next_status": status.value, "actor": actor, **({"reason": reason.strip()} if reason and reason.strip() else {})}
        self._append_audit_log(organization_id, incident_id, f"incident.{status.value}", previous.value, status.value, actor, now, meta)
        return incident

    def audit_logs(self, organization_id: str, incident_id: str) -> list[AuditLogEntry]:
        if self.session_factory is None or select is None:
            return []
        from .models import IncidentAuditLog as IncidentAuditLogRow
        with self.session_factory() as session:
            items: list[AuditLogEntry] = []
            for row in session.execute(select(IncidentAuditLogRow).where(IncidentAuditLogRow.organization_id == organization_id, IncidentAuditLogRow.incident_id == incident_id)).scalars().all():
                items.append(AuditLogEntry(id=row.id, organization_id=row.organization_id, incident_id=row.incident_id, action=row.action, from_status=row.from_status, to_status=row.to_status, actor=row.actor, created_at=self._ensure_aware_utc(row.created_at, default_now=True) or datetime.now(timezone.utc), metadata=json.loads(row.metadata_json or "{}")))
            return items


class SqlAlchemyEvidenceRepository:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def _ensure_aware_utc(self, value: datetime | None, default_now: bool = False) -> datetime | None:
        if value is None:
            return datetime.now(timezone.utc) if default_now else None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def _to_domain(self, row: EvidenceMetadataRow | None):
        from ..domain.evidence import IncidentEvidence, EvidenceKind, EvidenceSource
        if row is None:
            return None
        return IncidentEvidence(
            organization_id=row.organization_id,
            incident_id=row.incident_id,
            file_id=row.file_id,
            object_key=row.object_key,
            media_type=row.media_type,
            size=row.size,
            source=EvidenceSource(row.source),
            uploaded_by=row.uploaded_by,
            kind=EvidenceKind(row.kind),
            created_at=cast(datetime, self._ensure_aware_utc(row.created_at, default_now=True)),
            deleted_at=self._ensure_aware_utc(getattr(row, "deleted_at", None)),
            metadata=json.loads(row.metadata_json or "{}"),
        )

    def save(self, evidence) -> None:
        if self.session_factory is None:
            raise RuntimeError("SQLAlchemy not available")
        with self.session_factory() as session:
            existing = None
            if select is not None:
                existing = session.execute(select(EvidenceMetadataRow).where(EvidenceMetadataRow.organization_id == evidence.organization_id, EvidenceMetadataRow.incident_id == evidence.incident_id, EvidenceMetadataRow.file_id == evidence.file_id)).scalar_one_or_none()
            row = EvidenceMetadataRow(
                id=existing.id if existing is not None else new_id(),
                organization_id=evidence.organization_id,
                incident_id=evidence.incident_id,
                file_id=evidence.file_id,
                object_key=evidence.object_key,
                media_type=evidence.media_type,
                size=evidence.size,
                source=evidence.source.value,
                uploaded_by=evidence.uploaded_by,
                kind=evidence.kind.value,
                created_at=evidence.created_at,
                deleted_at=evidence.deleted_at,
                metadata_json=json.dumps(evidence.metadata),
            )
            session.merge(row)
            session.commit()

    def get(self, organization_id: str, incident_id: str, file_id: str):
        if self.session_factory is None or select is None:
            return None
        with self.session_factory() as session:
            row = session.execute(select(EvidenceMetadataRow).where(EvidenceMetadataRow.organization_id == organization_id, EvidenceMetadataRow.incident_id == incident_id, EvidenceMetadataRow.file_id == file_id)).scalar_one_or_none()
            return self._to_domain(row)

    def list_by_organization(self, organization_id: str):
        if self.session_factory is None or select is None:
            return []
        with self.session_factory() as session:
            items = []
            for row in session.execute(select(EvidenceMetadataRow).where(EvidenceMetadataRow.organization_id == organization_id)).scalars().all():
                evidence = self._to_domain(row)
                if evidence is not None:
                    items.append(evidence)
            return items

    def list_by_incident(self, organization_id: str, incident_id: str):
        if self.session_factory is None or select is None:
            return []
        with self.session_factory() as session:
            items = []
            for row in session.execute(select(EvidenceMetadataRow).where(EvidenceMetadataRow.organization_id == organization_id, EvidenceMetadataRow.incident_id == incident_id)).scalars().all():
                evidence = self._to_domain(row)
                if evidence is not None:
                    items.append(evidence)
            return items

    def mark_deleted(self, organization_id: str, incident_id: str, file_id: str, deleted_at: datetime | None = None) -> None:
        if self.session_factory is None:
            return
        deleted_at = self._ensure_aware_utc(deleted_at, default_now=True)
        with self.session_factory() as session:
            if select is None:
                return
            row = session.execute(select(EvidenceMetadataRow).where(EvidenceMetadataRow.organization_id == organization_id, EvidenceMetadataRow.incident_id == incident_id, EvidenceMetadataRow.file_id == file_id)).scalar_one_or_none()
            if row is None:
                return
            row.deleted_at = deleted_at
            session.commit()

    def append_audit_log(self, organization_id: str, actor_user_id: str, action: str, incident_id: str, file_id: str, created_at: datetime | None = None, metadata: dict[str, Any] | None = None) -> None:
        if self.session_factory is None:
            return
        created_at = self._ensure_aware_utc(created_at, default_now=True)
        with self.session_factory() as session:
            session.add(EvidenceAccessAuditLogRow(id=new_id(), organization_id=organization_id, actor_user_id=actor_user_id, action=action, incident_id=incident_id, file_id=file_id, created_at=created_at or datetime.now(timezone.utc), metadata_json=json.dumps(metadata or {})))
            session.commit()

    def audit_logs(self, organization_id: str, incident_id: str):
        if self.session_factory is None or select is None:
            return []
        with self.session_factory() as session:
            return [
                EvidenceAccessAuditLog(
                    id=row.id,
                    organization_id=row.organization_id,
                    actor_user_id=row.actor_user_id,
                    action=row.action,
                    incident_id=row.incident_id,
                    file_id=row.file_id,
                    created_at=self._ensure_aware_utc(row.created_at, default_now=True) or datetime.now(timezone.utc),
                    metadata=json.loads(row.metadata_json or "{}"),
                )
                for row in session.execute(select(EvidenceAccessAuditLogRow).where(EvidenceAccessAuditLogRow.organization_id == organization_id, EvidenceAccessAuditLogRow.incident_id == incident_id)).scalars().all()
            ]

    def list_audit_logs(self, organization_id: str):
        if self.session_factory is None or select is None:
            return []
        with self.session_factory() as session:
            return [
                EvidenceAccessAuditLog(
                    id=row.id,
                    organization_id=row.organization_id,
                    actor_user_id=row.actor_user_id,
                    action=row.action,
                    incident_id=row.incident_id,
                    file_id=row.file_id,
                    created_at=self._ensure_aware_utc(row.created_at, default_now=True) or datetime.now(timezone.utc),
                    metadata=json.loads(row.metadata_json or "{}"),
                )
                for row in session.execute(select(EvidenceAccessAuditLogRow).where(EvidenceAccessAuditLogRow.organization_id == organization_id)).scalars().all()
            ]


class SqlAlchemyEdgeWorkerRepository:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def _ensure_aware_utc(self, value: datetime | None, default_now: bool = False) -> datetime | None:
        if value is None:
            return datetime.now(timezone.utc) if default_now else None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def save(self, worker: EdgeWorker) -> None:
        if self.session_factory is None:
            raise RuntimeError("SQLAlchemy not available")
        with self.session_factory() as session:
            row = EdgeWorkerRow(
                id=worker.id,
                organization_id=worker.organization_id,
                site_id=worker.site_id,
                name=worker.name,
                client_id=worker.client_id,
                api_key_hash=worker.api_key_hash,
                status=worker.status.value,
                last_heartbeat_at=worker.last_heartbeat_at,
                allowed_camera_ids=json.dumps(worker.allowed_camera_ids),
                created_at=worker.created_at,
                updated_at=worker.updated_at,
            )
            session.merge(row)
            session.commit()

    def _to_domain(self, row: EdgeWorkerRow | None) -> EdgeWorker | None:
        if row is None:
            return None
        return EdgeWorker(
            id=row.id,
            organization_id=row.organization_id,
            site_id=row.site_id,
            name=row.name,
            client_id=row.client_id,
            api_key_hash=row.api_key_hash,
            allowed_camera_ids=json.loads(row.allowed_camera_ids or "[]"),
            status=EdgeWorkerStatus(row.status),
            last_heartbeat_at=self._ensure_aware_utc(row.last_heartbeat_at),
            created_at=cast(datetime, self._ensure_aware_utc(row.created_at, default_now=True)),
            updated_at=cast(datetime, self._ensure_aware_utc(row.updated_at, default_now=True)),
        )

    def get(self, worker_id: str) -> EdgeWorker | None:
        if self.session_factory is None:
            return None
        with self.session_factory() as session:
            return self._to_domain(session.get(EdgeWorkerRow, worker_id))

    def get_by_client_id(self, client_id: str) -> EdgeWorker | None:
        if self.session_factory is None or select is None:
            return None
        with self.session_factory() as session:
            return self._to_domain(session.execute(select(EdgeWorkerRow).where(EdgeWorkerRow.client_id == client_id)).scalar_one_or_none())

    def list_by_organization(self, organization_id: str) -> list[EdgeWorker]:
        if self.session_factory is None or select is None:
            return []
        with self.session_factory() as session:
            items: list[EdgeWorker] = []
            for row in session.execute(select(EdgeWorkerRow).where(EdgeWorkerRow.organization_id == organization_id)).scalars().all():
                worker = self._to_domain(row)
                if worker is not None:
                    items.append(worker)
            return items

    def list_all(self) -> list[EdgeWorker]:
        if self.session_factory is None or select is None:
            return []
        with self.session_factory() as session:
            items: list[EdgeWorker] = []
            for row in session.execute(select(EdgeWorkerRow)).scalars().all():
                worker = self._to_domain(row)
                if worker is not None:
                    items.append(worker)
            return items

    def delete(self, worker_id: str) -> None:
        if self.session_factory is None or select is None:
            return
        with self.session_factory() as session:
            row = session.get(EdgeWorkerRow, worker_id)
            if row is not None:
                session.delete(row)
                session.commit()

    def update_last_heartbeat(self, worker_id: str, last_heartbeat_at) -> None:
        if self.session_factory is None:
            return
        with self.session_factory() as session:
            row = session.get(EdgeWorkerRow, worker_id)
            if row is None:
                return
            row.last_heartbeat_at = last_heartbeat_at
            session.commit()

    def update_status(self, worker_id: str, status: str | EdgeWorkerStatus) -> None:
        if self.session_factory is None:
            return
        with self.session_factory() as session:
            row = session.get(EdgeWorkerRow, worker_id)
            if row is None:
                return
            row.status = getattr(status, "value", status)
            session.commit()
