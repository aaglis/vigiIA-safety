from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from ..domain.auth import User
from ..domain.invites import InviteStatus, OrganizationInvite, QueuedEmail
from typing import Any

from .auth import InMemoryAuthRepository
from .security import generate_token, hash_password, hash_token
from ..security.permissions import has_permission


class InMemoryInviteRepository:
    def __init__(self) -> None:
        self.invites: dict[str, OrganizationInvite] = {}
        self.emails: list[QueuedEmail] = []
        self.audit_logs: list[dict[str, str]] = []

    def save(self, invite: OrganizationInvite) -> None:
        self.invites[invite.id] = invite

    def get(self, invite_id: str) -> OrganizationInvite | None:
        return self.invites.get(invite_id)

    def find_by_token_hash(self, token_hash: str) -> OrganizationInvite | None:
        return next((invite for invite in self.invites.values() if invite.token_hash == token_hash), None)

    def list_by_organization(self, organization_id: str) -> list[OrganizationInvite]:
        return [invite for invite in self.invites.values() if invite.organization_id == organization_id]

    def queue_email(self, email: QueuedEmail) -> None:
        self.emails.append(email)

    def add_audit(self, entry: dict[str, str]) -> None:
        self.audit_logs.append(entry)


class InviteService:
    def __init__(self, auth_repository: Any | None = None, repository: Any | None = None) -> None:
        self.auth_repository = auth_repository or InMemoryAuthRepository()
        self.repository = repository or InMemoryInviteRepository()

    def _require_invite(self, invite_id: str) -> OrganizationInvite:
        invite = self.repository.get(invite_id)
        if invite is None:
            raise KeyError(invite_id)
        return invite

    def _allowed_roles_for(self, inviter_role: str) -> set[str]:
        if inviter_role in {"org_owner", "org_admin"}:
            return {"org_admin", "manager", "auditor_viewer"}
        if inviter_role == "manager":
            return {"auditor_viewer"}
        return set()

    def _audit(self, action: str, invite_id: str, organization_id: str, actor_user_id: str) -> None:
        self.repository.add_audit({"action": action, "invite_id": invite_id, "organization_id": organization_id, "actor_user_id": actor_user_id})

    def create_invite(self, organization_id: str, email: str, role: str, invited_by_user_id: str, inviter_role: str, permissions: list[str] | None = None) -> tuple[OrganizationInvite, str]:
        if role not in self._allowed_roles_for(inviter_role):
            raise PermissionError("inviter cannot assign this role")
        if permissions and not all(has_permission(inviter_role, perm) for perm in permissions):
            raise PermissionError("inviter lacks permission for invite scope")
        token = generate_token(32)
        invite = OrganizationInvite(id=generate_token(), organization_id=organization_id, email=email.lower(), role=role, invited_by_user_id=invited_by_user_id, token_hash=hash_token(token), expires_at=datetime.now(timezone.utc) + timedelta(days=7))
        self.repository.save(invite)
        self.repository.queue_email(QueuedEmail(id=generate_token(), to_email=invite.email, subject="Invitation to VigIA", body=f"Use token: {token}", organization_id=organization_id, invite_id=invite.id))
        self._audit("invite.created", invite.id, organization_id, invited_by_user_id)
        return invite, token

    def list_invites(self, organization_id: str) -> list[OrganizationInvite]:
        return self.repository.list_by_organization(organization_id)

    def resend_invite(self, invite_id: str) -> str:
        invite = self._require_invite(invite_id)
        if invite.status != InviteStatus.PENDING:
            raise ValueError("invite not pending")
        token = generate_token(32)
        invite.token_hash = hash_token(token)
        invite.updated_at = datetime.now(timezone.utc)
        self.repository.save(invite)
        self.repository.queue_email(QueuedEmail(id=generate_token(), to_email=invite.email, subject="Invitation to VigIA", body=f"Use token: {token}", organization_id=invite.organization_id, invite_id=invite.id))
        self._audit("invite.resend", invite.id, invite.organization_id, invite.invited_by_user_id)
        return token

    def revoke_invite(self, invite_id: str) -> OrganizationInvite:
        invite = self._require_invite(invite_id)
        if invite.status != InviteStatus.PENDING:
            raise ValueError("invite not pending")
        invite.status = InviteStatus.REVOKED
        invite.revoked_at = datetime.now(timezone.utc)
        invite.updated_at = invite.revoked_at
        self.repository.save(invite)
        self._audit("invite.revoked", invite.id, invite.organization_id, invite.invited_by_user_id)
        return invite

    def accept_invite(self, token: str, email: str, full_name: str, password: str | None = None) -> User:
        invite = self.repository.find_by_token_hash(hash_token(token))
        if not invite:
            raise ValueError("invalid invite token")
        now = datetime.now(timezone.utc)
        if invite.status != InviteStatus.PENDING:
            raise ValueError("invite not available")
        if invite.expires_at < now:
            invite.status = InviteStatus.EXPIRED
            self.repository.save(invite)
            raise ValueError("invite expired")
        if invite.email != email.lower():
            raise ValueError("invite email mismatch")
        user = self.auth_repository.get_user_by_email(email)
        if not user:
            user = User(id=uuid4().hex, email=email.lower(), full_name=full_name, password_hash=hash_password(password or generate_token(16)))
            self.auth_repository.add_user(user)
        self.auth_repository.add_membership(invite.organization_id, user.id, invite.role)
        invite.status = InviteStatus.ACCEPTED
        invite.accepted_at = now
        invite.accepted_by_user_id = user.id
        invite.updated_at = now
        self.repository.save(invite)
        self._audit("invite.accepted", invite.id, invite.organization_id, user.id)
        return user
