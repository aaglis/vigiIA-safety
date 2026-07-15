from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class EvidenceSource(StrEnum):
    USER = "user"
    EDGE_WORKER = "edge_worker"


class EvidenceKind(StrEnum):
    SNAPSHOT = "snapshot"
    CLIP = "clip"
    METADATA = "metadata"


@dataclass
class IncidentEvidence:
    organization_id: str
    incident_id: str
    file_id: str
    object_key: str
    media_type: str
    size: int
    source: EvidenceSource
    uploaded_by: str
    kind: EvidenceKind = EvidenceKind.SNAPSHOT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceRetentionPolicy:
    organization_id: str
    metadata_days: int = 180
    snapshot_days: int = 30
    clip_days: int = 30
    audit_log_days: int = 365
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class EvidenceAccessAuditLog:
    id: str
    organization_id: str
    actor_user_id: str
    action: str
    incident_id: str
    file_id: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)


class EvidencePurgeError(ValueError):
    pass
