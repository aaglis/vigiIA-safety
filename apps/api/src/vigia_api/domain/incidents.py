from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class IncidentStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


@dataclass(frozen=True)
class DetectionEvent:
    organization_id: str
    event_id: str
    site_id: str | None
    camera_id: str
    zone_id: str
    worker_id: str | None
    event_type: str
    severity: str
    detected_at: datetime
    summary: str
    confidence: float | None = None
    model_version: str | None = None
    evidence: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Incident:
    id: str
    organization_id: str
    site_id: str | None
    detection_event_id: str
    camera_id: str
    zone_id: str
    worker_id: str | None
    event_type: str
    severity: str
    summary: str
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    status: IncidentStatus = IncidentStatus.OPEN
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    resolution_reason: str | None = None
    dismissed_at: datetime | None = None
    dismissed_by: str | None = None
    dismiss_reason: str | None = None


@dataclass(frozen=True)
class AuditLogEntry:
    id: str
    organization_id: str
    incident_id: str
    action: str
    from_status: str | None
    to_status: str
    actor: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NotificationAttempt:
    id: str
    organization_id: str
    incident_id: str
    channel: str
    status: str
    created_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)


def new_id() -> str:
    return uuid4().hex


def parse_detection_event(payload: dict[str, Any]) -> DetectionEvent:
    detected_at = payload.get("timestamp") or payload.get("detected_at")
    if isinstance(detected_at, str):
        detected_at = datetime.fromisoformat(detected_at.replace("Z", "+00:00"))
    elif not isinstance(detected_at, datetime):
        detected_at = datetime.now(timezone.utc)
    return DetectionEvent(
        organization_id=str(payload["organization_id"]),
        event_id=str(payload.get("event_id") or new_id()),
        site_id=str(payload.get("site_id")) if payload.get("site_id") is not None else None,
        camera_id=str(payload["camera_id"]),
        zone_id=str(payload["zone_id"]),
        worker_id=str(payload.get("worker_id")) if payload.get("worker_id") is not None else None,
        event_type=str(payload.get("event_type") or payload.get("type") or "detection"),
        severity=str(payload["severity"]),
        detected_at=detected_at,
        summary=str(payload.get("summary") or "Detection event"),
        confidence=payload.get("confidence"),
        model_version=payload.get("model_version"),
        evidence=payload.get("evidence") if isinstance(payload.get("evidence"), dict) else None,
        metadata={k: v for k, v in dict(payload.get("metadata") or {}).items() if k not in {"evidence"}},
    )
