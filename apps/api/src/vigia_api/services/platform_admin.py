from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from ..domain.auth import PlatformRole, User
from ..domain.platform import Organization, OrganizationStatus, PlatformAuditLog
from typing import Any

from .auth import InMemoryAuthRepository
from .security import generate_token, hash_password


class PlatformAdminService:
    def __init__(self, auth_repository: Any | None = None) -> None:
        self.auth_repository = auth_repository or InMemoryAuthRepository()
        self.organizations: dict[str, Organization] = {}
        self.audit_logs: list[PlatformAuditLog] = []

    def require_platform_admin(self, user: User) -> None:
        if user.platform_role not in {PlatformRole.PLATFORM_ADMIN, PlatformRole.PLATFORM_OWNER}:
            raise PermissionError("insufficient platform permissions")

    def _audit(self, action: str, organization_id: str | None, actor_user_id: str, **metadata: str) -> None:
        self.audit_logs.append(PlatformAuditLog(id=generate_token(), action=action, organization_id=organization_id, actor_user_id=actor_user_id, created_at=datetime.now(timezone.utc), metadata=metadata))

    def _resolve_user(self, email: str | None, created_by_user_id: str) -> User:
        if email:
            user = self.auth_repository.get_user_by_email(email)
            if user:
                return user
            user = User(id=generate_token(), email=email.lower(), full_name=email.split("@")[0].replace(".", " ").title(), password_hash=hash_password(generate_token(32)))
            self.auth_repository.add_user(user)
            return user
        return self.auth_repository.users[created_by_user_id]

    def create_organization(self, *, name: str, legal_name: str, tax_id: str, created_by_user_id: str, plan: str | None = None, leader_email: str | None = None) -> Organization:
        creator = self.auth_repository.users[created_by_user_id]
        self.require_platform_admin(creator)
        organization = Organization(id=generate_token(), name=name, legal_name=legal_name, tax_id=tax_id, plan=plan, created_by_user_id=created_by_user_id)
        self.organizations[organization.id] = organization
        leader = self._resolve_user(leader_email, created_by_user_id)
        self.auth_repository.memberships.setdefault(leader.id, [])
        self._audit("organization.created", organization.id, created_by_user_id, name=name, leader_user_id=leader.id)
        self._audit("organization.owner_assigned", organization.id, created_by_user_id, user_id=leader.id)
        return organization

    def list_organizations(self) -> list[dict[str, object]]:
        return [{"organization": asdict(org), "health": {"status": org.status.value, "retention_days": org.retention_days}} for org in self.organizations.values()]

    def suspend_organization(self, organization_id: str, actor_user_id: str) -> Organization:
        actor = self.auth_repository.users[actor_user_id]
        self.require_platform_admin(actor)
        organization = self.organizations[organization_id]
        organization.status = OrganizationStatus.SUSPENDED
        organization.updated_at = datetime.now(timezone.utc)
        self._audit("organization.suspended", organization_id, actor_user_id)
        return organization

    def reactivate_organization(self, organization_id: str, actor_user_id: str) -> Organization:
        actor = self.auth_repository.users[actor_user_id]
        self.require_platform_admin(actor)
        organization = self.organizations[organization_id]
        organization.status = OrganizationStatus.ACTIVE
        organization.updated_at = datetime.now(timezone.utc)
        self._audit("organization.reactivated", organization_id, actor_user_id)
        return organization
