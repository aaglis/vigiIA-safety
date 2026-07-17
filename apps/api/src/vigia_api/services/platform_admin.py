from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from uuid import uuid4

from ..domain.auth import PlatformRole, User
from ..domain.platform import Organization, OrganizationStatus, PlatformAuditLog
from typing import Any

from .auth import InMemoryAuthRepository
from .security import generate_token, hash_password


class InMemoryPlatformRepository:
    def __init__(self) -> None:
        self.organizations: dict[str, Organization] = {}

    def save(self, organization: Organization) -> None:
        self.organizations[organization.id] = organization

    def get(self, organization_id: str) -> Organization | None:
        return self.organizations.get(organization_id)

    def list_all(self) -> list[Organization]:
        return list(self.organizations.values())


class PlatformAdminService:
    def __init__(self, auth_repository: Any | None = None, repository: Any | None = None) -> None:
        self.auth_repository = auth_repository or InMemoryAuthRepository()
        self.repository = repository or InMemoryPlatformRepository()
        self.audit_logs: list[PlatformAuditLog] = []

    @property
    def organizations(self) -> dict[str, Organization]:
        """Compatibilidade: leitura por dict continua funcionando sobre o repositório."""
        return {org.id: org for org in self.repository.list_all()}

    def require_platform_admin(self, user: User) -> None:
        if user.platform_role not in {PlatformRole.PLATFORM_ADMIN, PlatformRole.PLATFORM_OWNER}:
            raise PermissionError("insufficient platform permissions")

    def _audit(self, action: str, organization_id: str | None, actor_user_id: str, **metadata: str) -> None:
        self.audit_logs.append(PlatformAuditLog(id=uuid4().hex, action=action, organization_id=organization_id, actor_user_id=actor_user_id, created_at=datetime.now(timezone.utc), metadata=metadata))

    def _require_user(self, user_id: str) -> User:
        user = self.auth_repository.get_user_by_id(user_id)
        if user is None:
            raise KeyError(user_id)
        return user

    def _require_organization(self, organization_id: str) -> Organization:
        organization = self.repository.get(organization_id)
        if organization is None:
            raise KeyError(organization_id)
        return organization

    def _resolve_user(self, email: str | None, created_by_user_id: str) -> User:
        if email:
            user = self.auth_repository.get_user_by_email(email)
            if user:
                return user
            user = User(id=uuid4().hex, email=email.lower(), full_name=email.split("@")[0].replace(".", " ").title(), password_hash=hash_password(generate_token(32)))
            self.auth_repository.add_user(user)
            return user
        return self._require_user(created_by_user_id)

    def create_organization(self, *, name: str, legal_name: str, tax_id: str, created_by_user_id: str, plan: str | None = None, leader_email: str | None = None) -> Organization:
        creator = self._require_user(created_by_user_id)
        self.require_platform_admin(creator)
        organization = Organization(id=uuid4().hex, name=name, legal_name=legal_name, tax_id=tax_id, plan=plan, created_by_user_id=created_by_user_id)
        self.repository.save(organization)
        leader = self._resolve_user(leader_email, created_by_user_id)
        # O líder precisa do vínculo de fato (antes só criava uma lista vazia).
        self.auth_repository.add_membership(organization.id, leader.id, "org_owner")
        self._audit("organization.created", organization.id, created_by_user_id, name=name, leader_user_id=leader.id)
        self._audit("organization.owner_assigned", organization.id, created_by_user_id, user_id=leader.id)
        return organization

    def list_organizations(self) -> list[dict[str, object]]:
        return [{"organization": asdict(org), "health": {"status": org.status.value, "retention_days": org.retention_days}} for org in self.repository.list_all()]

    def _set_status(self, organization_id: str, actor_user_id: str, status: OrganizationStatus, action: str) -> Organization:
        actor = self._require_user(actor_user_id)
        self.require_platform_admin(actor)
        organization = self._require_organization(organization_id)
        organization.status = status
        organization.updated_at = datetime.now(timezone.utc)
        self.repository.save(organization)
        self._audit(action, organization_id, actor_user_id)
        return organization

    def suspend_organization(self, organization_id: str, actor_user_id: str) -> Organization:
        return self._set_status(organization_id, actor_user_id, OrganizationStatus.SUSPENDED, "organization.suspended")

    def reactivate_organization(self, organization_id: str, actor_user_id: str) -> Organization:
        return self._set_status(organization_id, actor_user_id, OrganizationStatus.ACTIVE, "organization.reactivated")
