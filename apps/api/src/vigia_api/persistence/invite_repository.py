from __future__ import annotations

from datetime import datetime, timezone

try:
    from sqlalchemy import select  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    select = None  # type: ignore[assignment]

from ..domain.invites import InviteStatus, OrganizationInvite, QueuedEmail
from .models import OrganizationInvite as InviteRow


class SqlAlchemyInviteRepository:
    """Convites persistidos. A fila de e-mail e o audit ficam em memória por enquanto
    (o envio real é responsabilidade do notifier; ver services/notifications.py)."""

    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory
        self.emails: list[QueuedEmail] = []
        self.audit_logs: list[dict[str, str]] = []

    def _ensure_aware(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    def _to_domain(self, row: InviteRow | None) -> OrganizationInvite | None:
        if row is None:
            return None
        return OrganizationInvite(
            id=row.id,
            organization_id=row.organization_id,
            email=row.email,
            role=row.role,
            invited_by_user_id=row.invited_by_user_id,
            token_hash=row.token_hash,
            status=InviteStatus(row.status),
            expires_at=self._ensure_aware(row.expires_at),
            created_at=self._ensure_aware(row.created_at),
            updated_at=self._ensure_aware(row.updated_at),
            accepted_at=self._ensure_aware(row.accepted_at),
            revoked_at=self._ensure_aware(row.revoked_at),
            accepted_by_user_id=row.accepted_by_user_id,
        )

    def save(self, invite: OrganizationInvite) -> None:
        with self.session_factory() as session:
            session.merge(
                InviteRow(
                    id=invite.id,
                    organization_id=invite.organization_id,
                    email=invite.email,
                    role=invite.role,
                    invited_by_user_id=invite.invited_by_user_id,
                    token_hash=invite.token_hash,
                    status=invite.status.value,
                    expires_at=invite.expires_at,
                    created_at=invite.created_at,
                    updated_at=invite.updated_at,
                    accepted_at=invite.accepted_at,
                    revoked_at=invite.revoked_at,
                    accepted_by_user_id=invite.accepted_by_user_id,
                )
            )
            session.commit()

    def get(self, invite_id: str) -> OrganizationInvite | None:
        with self.session_factory() as session:
            return self._to_domain(session.get(InviteRow, invite_id))

    def find_by_token_hash(self, token_hash: str) -> OrganizationInvite | None:
        if select is None:
            return None
        with self.session_factory() as session:
            row = session.execute(select(InviteRow).where(InviteRow.token_hash == token_hash)).scalars().first()
            return self._to_domain(row)

    def list_by_organization(self, organization_id: str) -> list[OrganizationInvite]:
        if select is None:
            return []
        with self.session_factory() as session:
            rows = session.execute(select(InviteRow).where(InviteRow.organization_id == organization_id)).scalars().all()
            return [invite for invite in (self._to_domain(row) for row in rows) if invite is not None]

    def queue_email(self, email: QueuedEmail) -> None:
        self.emails.append(email)

    def add_audit(self, entry: dict[str, str]) -> None:
        self.audit_logs.append(entry)
