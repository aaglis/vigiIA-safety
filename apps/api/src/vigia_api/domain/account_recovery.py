from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


class RecoveryTokenStatus(StrEnum):
    PENDING = "pending"
    USED = "used"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class PasswordResetToken:
    id: str
    user_id: str
    email: str
    token_hash: str
    status: RecoveryTokenStatus = RecoveryTokenStatus.PENDING
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    used_at: datetime | None = None
    revoked_at: datetime | None = None


@dataclass
class EmailVerificationToken:
    id: str
    user_id: str
    email: str
    token_hash: str
    status: RecoveryTokenStatus = RecoveryTokenStatus.PENDING
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    used_at: datetime | None = None


@dataclass(frozen=True)
class QueuedRecoveryEmail:
    id: str
    to_email: str
    subject: str
    body: str
    purpose: str
    user_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class RecoveryAuditLog:
    id: str
    action: str
    user_id: str | None
    email: str | None
    created_at: datetime
    metadata: dict[str, str] = field(default_factory=dict)
