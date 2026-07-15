from __future__ import annotations

import json
from datetime import datetime, timezone

try:
    from sqlalchemy import select
except Exception:  # pragma: no cover
    select = None  # type: ignore[assignment]

from ..domain.auth import MembershipSummary, OrganizationSummary, Permission, PlatformRole, User, UserSession
from ..security.permissions import role_permissions
from ..services.security import hash_password
from ..settings import settings
from .models import Organization as OrganizationRow, OrganizationMembership as OrganizationMembershipRow, User as UserRow, UserSession as UserSessionRow


class SqlAlchemyAuthRepository:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def _ensure_aware_utc(self, value: datetime | None, default_now: bool = False) -> datetime | None:
        if value is None:
            return datetime.now(timezone.utc) if default_now else None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def seed_demo_user(self) -> None:
        if settings.app_env.lower() not in {"dev", "demo", "local"}:
            return
        with self.session_factory() as session:
            org = session.execute(select(OrganizationRow).where(OrganizationRow.id == "org-demo")).scalar_one_or_none() if select is not None else None
            if org is None:
                org = OrganizationRow(id="org-demo", name="VigIA Local", legal_name="VigIA Local Demo", tax_id="DEMO-ORG-001", status="active", retention_days=365, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
                session.add(org)
            user = session.execute(select(UserRow).where(UserRow.email_normalized == "admin@vigia.local")).scalar_one_or_none() if select is not None else None
            if user is None:
                user = UserRow(id="user-dev", email="admin@vigia.local", email_normalized="admin@vigia.local", full_name="VigIA Admin", password_hash=hash_password("change-me-dev"), platform_role=PlatformRole.NONE.value, is_active=True, email_verified_at=datetime.now(timezone.utc), created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc))
                session.add(user)
                session.flush()
            membership = session.execute(select(OrganizationMembershipRow).where(OrganizationMembershipRow.organization_id == "org-demo", OrganizationMembershipRow.user_id == user.id)).scalar_one_or_none() if select is not None else None
            if membership is None:
                session.add(OrganizationMembershipRow(id="membership-demo-owner", organization_id="org-demo", user_id=user.id, role="org_owner", status="active", invited_by=None, joined_at=datetime.now(timezone.utc), created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)))
            session.commit()

    def add_user(self, user: User) -> None:
        with self.session_factory() as session:
            session.merge(UserRow(id=user.id, email=user.email, email_normalized=user.email.lower(), full_name=user.full_name, password_hash=user.password_hash, platform_role=user.platform_role.value, is_active=user.is_active, email_verified_at=user.email_verified_at, created_at=user.created_at, updated_at=user.created_at))
            session.commit()

    def get_user_by_email(self, email: str) -> User | None:
        if select is None:
            return None
        with self.session_factory() as session:
            row = session.execute(select(UserRow).where(UserRow.email_normalized == email.lower())).scalar_one_or_none()
            return self._to_user(row)

    def get_user_by_id(self, user_id: str) -> User | None:
        if select is None:
            return None
        with self.session_factory() as session:
            return self._to_user(session.get(UserRow, user_id))

    def _to_user(self, row: UserRow | None) -> User | None:
        if row is None:
            return None
        return User(id=row.id, email=row.email, full_name=row.full_name, password_hash=row.password_hash, platform_role=PlatformRole(row.platform_role), is_active=row.is_active, email_verified_at=self._ensure_aware_utc(row.email_verified_at), created_at=self._ensure_aware_utc(row.created_at, default_now=True) or datetime.now(timezone.utc))

    def update_password_hash(self, user_id: str, password_hash: str) -> None:
        with self.session_factory() as session:
            row = session.get(UserRow, user_id)
            if row is not None:
                row.password_hash = password_hash
                session.commit()

    def revoke_sessions_for_user(self, user_id: str) -> None:
        with self.session_factory() as session:
            if select is None:
                return
            for row in session.execute(select(UserSessionRow).where(UserSessionRow.user_id == user_id, UserSessionRow.revoked_at.is_(None))).scalars().all():
                row.revoked_at = datetime.now(timezone.utc)
            session.commit()

    def mark_email_verified(self, user_id: str) -> None:
        with self.session_factory() as session:
            row = session.get(UserRow, user_id)
            if row is not None:
                row.email_verified_at = datetime.now(timezone.utc)
                session.commit()

    def save_session(self, session_obj: UserSession) -> None:
        with self.session_factory() as session:
            session.merge(UserSessionRow(id=session_obj.id, user_id=session_obj.user_id, refresh_token_hash=session_obj.refresh_token_hash, expires_at=session_obj.expires_at, revoked_at=session_obj.revoked_at, created_at=session_obj.created_at, last_used_at=session_obj.last_used_at, user_agent=session_obj.user_agent, ip_address=session_obj.ip_address, active_organization_id=session_obj.active_organization_id))
            session.commit()

    def get_session(self, session_id: str) -> UserSession | None:
        if select is None:
            return None
        with self.session_factory() as session:
            return self._to_session(session.get(UserSessionRow, session_id))

    def get_session_by_refresh_token_hash(self, token_hash: str) -> UserSession | None:
        if select is None:
            return None
        with self.session_factory() as session:
            return self._to_session(session.execute(select(UserSessionRow).where(UserSessionRow.refresh_token_hash == token_hash)).scalar_one_or_none())

    def _to_session(self, row: UserSessionRow | None) -> UserSession | None:
        if row is None:
            return None
        return UserSession(id=row.id, user_id=row.user_id, refresh_token_hash=row.refresh_token_hash, expires_at=self._ensure_aware_utc(row.expires_at, default_now=True) or datetime.now(timezone.utc), revoked_at=self._ensure_aware_utc(row.revoked_at), created_at=self._ensure_aware_utc(row.created_at, default_now=True) or datetime.now(timezone.utc), last_used_at=self._ensure_aware_utc(row.last_used_at, default_now=True) or datetime.now(timezone.utc), user_agent=row.user_agent, ip_address=row.ip_address, active_organization_id=row.active_organization_id)

    def list_memberships(self, user_id: str) -> list[MembershipSummary]:
        if select is None:
            return []
        with self.session_factory() as session:
            items: list[MembershipSummary] = []
            stmt = select(OrganizationMembershipRow, OrganizationRow).join(OrganizationRow, OrganizationMembershipRow.organization_id == OrganizationRow.id).where(OrganizationMembershipRow.user_id == user_id)
            for membership_row, org_row in session.execute(stmt).all():
                items.append(MembershipSummary(organization=OrganizationSummary(id=org_row.id, name=org_row.name, slug=org_row.id), role=membership_row.role, permissions=[Permission(p) for p in role_permissions(membership_row.role) if p in Permission._value2member_map_], active=membership_row.status == "active"))
            return items
