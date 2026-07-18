from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


class Permission(StrEnum):
    VIEW_DASHBOARD = "view_dashboard"
    MANAGE_USERS = "manage_users"
    MANAGE_ORG = "manage_organization"


class PlatformRole(StrEnum):
    PLATFORM_OWNER = "platform_owner"
    PLATFORM_ADMIN = "platform_admin"
    PLATFORM_SUPPORT = "platform_support"
    NONE = "none"


@dataclass(frozen=True)
class OrganizationSummary:
    id: str
    name: str
    slug: str


@dataclass(frozen=True)
class MembershipSummary:
    organization: OrganizationSummary
    role: str
    permissions: list[str] = field(default_factory=list)
    active: bool = False


@dataclass
class User:
    id: str
    email: str
    full_name: str
    password_hash: str
    platform_role: PlatformRole = PlatformRole.NONE
    is_active: bool = True
    email_verified_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class UserSession:
    id: str
    user_id: str
    refresh_token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_agent: str | None = None
    ip_address: str | None = None
    active_organization_id: str | None = None


@dataclass(frozen=True)
class AuthTokens:
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    access_token_expires_in: int = 900


@dataclass(frozen=True)
class AuthenticatedUser:
    user: User
    memberships: list[MembershipSummary]
