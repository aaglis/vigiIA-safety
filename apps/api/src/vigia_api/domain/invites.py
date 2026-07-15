from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


class InviteStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class OrganizationInvite:
    id: str
    organization_id: str
    email: str
    role: str
    invited_by_user_id: str
    token_hash: str
    status: InviteStatus = InviteStatus.PENDING
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None
    accepted_by_user_id: str | None = None


@dataclass(frozen=True)
class QueuedEmail:
    id: str
    to_email: str
    subject: str
    body: str
    organization_id: str
    invite_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
