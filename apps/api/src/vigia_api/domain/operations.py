from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class EntityStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class ZoneType(StrEnum):
    ACCESS = "access"
    RESTRICTED = "restricted"
    PPE = "ppe"


@dataclass
class Site:
    id: str
    organization_id: str
    name: str
    address: str | None = None
    status: EntityStatus = EntityStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Department:
    id: str
    organization_id: str
    site_id: str
    name: str
    status: EntityStatus = EntityStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Worker:
    id: str
    organization_id: str
    name: str
    internal_id: str
    site_id: str | None = None
    department_id: str | None = None
    status: EntityStatus = EntityStatus.ACTIVE
    contact: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Camera:
    id: str
    organization_id: str
    site_id: str
    name: str
    stream_identifier: str
    status: EntityStatus = EntityStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Zone:
    id: str
    organization_id: str
    site_id: str
    camera_id: str
    zone_type: ZoneType
    polygon_json: dict[str, Any]
    status: EntityStatus = EntityStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SafetyRule:
    id: str
    organization_id: str
    site_id: str | None = None
    zone_id: str | None = None
    name: str = ""
    status: EntityStatus = EntityStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RequiredPPE:
    id: str
    organization_id: str
    rule_id: str
    site_id: str | None = None
    zone_id: str | None = None
    item: str = ""
    status: EntityStatus = EntityStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class OperationalAuditLog:
    id: str
    organization_id: str | None
    actor_user_id: str
    action: str
    target_type: str
    target_id: str
    ip: str | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
