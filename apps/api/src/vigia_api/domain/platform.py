from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


@dataclass
class Organization:
    id: str
    name: str
    legal_name: str
    tax_id: str
    status: OrganizationStatus = OrganizationStatus.ACTIVE
    plan: str | None = None
    retention_days: int = 365
    created_by_user_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class PlatformAuditLog:
    id: str
    action: str
    organization_id: str | None
    actor_user_id: str
    created_at: datetime
    metadata: dict[str, str] = field(default_factory=dict)
