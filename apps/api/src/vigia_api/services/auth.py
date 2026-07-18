from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast
from uuid import uuid4

from ..domain.auth import AuthTokens, AuthenticatedUser, MembershipSummary, OrganizationSummary, User, UserSession, PlatformRole
from ..settings import Settings, settings
from ..observability import log_event
from .security import decode_jwt, encode_jwt, generate_token, hash_password, hash_token, verify_password
from ..security.permissions import role_permissions


def _permissions_for_role(role: str):
    return sorted(role_permissions(role))


class InMemoryAuthRepository:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.users_by_email: dict[str, str] = {}
        self.sessions: dict[str, UserSession] = {}
        self.memberships: dict[str, list[MembershipSummary]] = {}

    def seed_demo_user(self) -> None:
        if "admin@vigia.local" in self.users_by_email:
            return
        user = User(id="user-dev", email="admin@vigia.local", full_name="VigIA Admin", password_hash=hash_password("change-me-dev"))
        self.add_user(user)
        org = OrganizationSummary(id="org-dev", name="VigIA Local", slug="vigia-local")
        self.memberships[user.id] = [MembershipSummary(organization=org, role="owner", permissions=_permissions_for_role("owner"), active=True)]

    def add_user(self, user: User) -> None:
        self.users[user.id] = user
        self.users_by_email[user.email.lower()] = user.id

    def get_user_by_email(self, email: str) -> User | None:
        user_id = self.users_by_email.get(email.lower())
        return self.users.get(user_id) if user_id else None

    def add_membership(self, organization_id: str, user_id: str, role: str, permissions: list | None = None) -> MembershipSummary:
        """Mesma interface do repositório SQL: idempotente por (org, user)."""
        org = OrganizationSummary(id=organization_id, name=organization_id, slug=organization_id)
        membership = MembershipSummary(organization=org, role=role, permissions=permissions or _permissions_for_role(role), active=True)
        current = self.memberships.setdefault(user_id, [])
        for index, existing in enumerate(current):
            if existing.organization.id == organization_id:
                current[index] = membership
                return membership
        current.append(membership)
        return membership

    def update_password_hash(self, user_id: str, password_hash: str) -> None:
        self.users[user_id].password_hash = password_hash

    def revoke_sessions_for_user(self, user_id: str) -> None:
        for session in self.sessions.values():
            if session.user_id == user_id and session.revoked_at is None:
                session.revoked_at = datetime.now(timezone.utc)

    def mark_email_verified(self, user_id: str) -> None:
        self.users[user_id].email_verified_at = datetime.now(timezone.utc)

    def get_user_by_id(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    def get_session(self, session_id: str) -> UserSession | None:
        return self.sessions.get(session_id)

    def get_session_by_refresh_token_hash(self, token_hash: str) -> UserSession | None:
        return next((s for s in self.sessions.values() if s.refresh_token_hash == token_hash), None)

    def save_session(self, session: UserSession) -> None:
        self.sessions[session.id] = session

    def list_memberships(self, user_id: str) -> list[MembershipSummary]:
        return cast(list[MembershipSummary], self.memberships.get(user_id, []))

    def list_organization_memberships(self, organization_id: str) -> list[tuple[User, MembershipSummary]]:
        items: list[tuple[User, MembershipSummary]] = []
        for user_id, memberships in self.memberships.items():
            user = self.users.get(user_id)
            if user is None:
                continue
            for membership in memberships:
                if membership.organization.id == organization_id:
                    items.append((user, membership))
        return items

    def update_organization_membership(self, organization_id: str, user_id: str, *, role: str | None = None, active: bool | None = None) -> tuple[User, MembershipSummary]:
        memberships = self.memberships.get(user_id, [])
        for idx, membership in enumerate(memberships):
            if membership.organization.id != organization_id:
                continue
            updated = MembershipSummary(organization=membership.organization, role=role or membership.role, permissions=_permissions_for_role(role or membership.role), active=membership.active if active is None else active)
            memberships[idx] = updated
            self.memberships[user_id] = memberships
            return self.users[user_id], updated
        raise KeyError("membership not found")

    def deactivate_organization_membership(self, organization_id: str, user_id: str) -> None:
        self.update_organization_membership(organization_id, user_id, active=False)


class SqlAuthRepositoryFallback(InMemoryAuthRepository):
    pass


class AuthService:
    def __init__(self, repository: Any | None = None, config: Settings | None = None) -> None:
        self.repository = repository or InMemoryAuthRepository()
        self.settings = config or settings
        if self.settings.app_env.lower() in {"dev", "demo", "local"}:
            self.repository.seed_demo_user()

    def _user_memberships(self, user_id: str) -> list[MembershipSummary]:
        get_memberships = getattr(self.repository, "list_memberships", None)
        if callable(get_memberships):
            return cast(list[MembershipSummary], get_memberships(user_id))
        return self.repository.memberships.get(user_id, [])

    def _get_user(self, user_id: str) -> User:
        get_user = getattr(self.repository, "get_user_by_id", None)
        user = get_user(user_id) if callable(get_user) else self.repository.users.get(user_id)
        if user is None:
            raise ValueError("invalid user")
        return cast(User, user)

    def _get_session(self, session_id: str) -> UserSession | None:
        get_session = getattr(self.repository, "get_session", None)
        session = get_session(session_id) if callable(get_session) else self.repository.sessions.get(session_id)
        return cast(UserSession | None, session)

    def _get_session_by_refresh_hash(self, token_hash: str) -> UserSession | None:
        get_session = getattr(self.repository, "get_session_by_refresh_token_hash", None)
        session = get_session(token_hash) if callable(get_session) else next((s for s in self.repository.sessions.values() if s.refresh_token_hash == token_hash), None)
        return cast(UserSession | None, session)

    def _save_session(self, session: UserSession) -> None:
        save_session = getattr(self.repository, "save_session", None)
        if callable(save_session):
            save_session(session)
        else:
            self.repository.sessions[session.id] = session

    def _new_session_id(self) -> str:
        return uuid4().hex

    def _serialize_user(self, user: User) -> dict[str, Any]:
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "platform_role": user.platform_role.value,
            "is_active": user.is_active,
            "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
            "created_at": user.created_at.isoformat(),
        }

    def _serialize_membership(self, membership: MembershipSummary) -> dict[str, Any]:
        return {
            "organization": {"id": membership.organization.id, "name": membership.organization.name, "slug": membership.organization.slug},
            "role": membership.role,
            "permissions": _permissions_for_role(membership.role),
            "active": membership.active,
        }

    def _serialize_member(self, user: User, membership: MembershipSummary) -> dict[str, Any]:
        return {"user": {"id": user.id, "email": user.email, "full_name": user.full_name}, "organization": {"id": membership.organization.id, "name": membership.organization.name, "slug": membership.organization.slug}, "role": membership.role, "permissions": _permissions_for_role(membership.role), "active": membership.active}

    def list_organization_memberships(self, organization_id: str) -> list[dict[str, Any]]:
        getter = getattr(self.repository, "list_organization_memberships", None)
        raw_pairs = getter(organization_id) if callable(getter) else []
        pairs = cast(list[tuple[User, MembershipSummary]], raw_pairs)
        return [self._serialize_member(user, membership) for user, membership in pairs]

    def update_organization_membership(self, organization_id: str, user_id: str, role: str | None = None, active: bool | None = None) -> dict[str, Any]:
        updater = getattr(self.repository, "update_organization_membership", None)
        if not callable(updater):
            raise ValueError("membership updates unavailable")
        user, membership = cast(tuple[User, MembershipSummary], updater(organization_id, user_id, role=role, active=active))
        return self._serialize_member(user, membership)

    def deactivate_organization_membership(self, organization_id: str, user_id: str) -> dict[str, Any]:
        return self.update_organization_membership(organization_id, user_id, active=False)

    def login(self, email: str, password: str, user_agent: str | None = None, ip_address: str | None = None) -> tuple[AuthTokens, UserSession, AuthenticatedUser]:
        user = self.repository.get_user_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            log_event("auth.login.failure", email_domain=email.split("@")[-1] if "@" in email else None)
            raise ValueError("invalid credentials")
        refresh_token = generate_token()
        session = UserSession(id=self._new_session_id(), user_id=user.id, refresh_token_hash=hash_token(refresh_token), expires_at=datetime.now(timezone.utc) + timedelta(days=30), user_agent=user_agent, ip_address=ip_address)
        self._save_session(session)
        access_token = encode_jwt({"sub": user.id, "sid": session.id}, self.settings.jwt_secret, self.settings.access_token_ttl_seconds)
        log_event("auth.login.success", organization_id=None, edge_worker_id=None, user_id=user.id, email_domain=user.email.split("@")[-1])
        return AuthTokens(access_token=access_token, refresh_token=refresh_token, access_token_expires_in=self.settings.access_token_ttl_seconds), session, AuthenticatedUser(user=user, memberships=self._user_memberships(user.id))

    def refresh(self, refresh_token: str) -> tuple[AuthTokens, UserSession, AuthenticatedUser]:
        token_hash = hash_token(refresh_token)
        session = self._get_session_by_refresh_hash(token_hash)
        if not session or session.revoked_at is not None or session.expires_at < datetime.now(timezone.utc):
            raise ValueError("invalid session")
        session.revoked_at = datetime.now(timezone.utc)
        self._save_session(session)
        user = self._get_user(session.user_id)
        new_refresh_token = generate_token()
        new_session = UserSession(id=self._new_session_id(), user_id=user.id, refresh_token_hash=hash_token(new_refresh_token), expires_at=datetime.now(timezone.utc) + timedelta(days=30), user_agent=session.user_agent, ip_address=session.ip_address, active_organization_id=session.active_organization_id)
        self._save_session(new_session)
        access_token = encode_jwt({"sub": user.id, "sid": new_session.id}, self.settings.jwt_secret, self.settings.access_token_ttl_seconds)
        log_event("auth.refresh", user_id=user.id)
        return AuthTokens(access_token=access_token, refresh_token=new_refresh_token, access_token_expires_in=self.settings.access_token_ttl_seconds), new_session, AuthenticatedUser(user=user, memberships=self._user_memberships(user.id))

    def logout(self, refresh_token: str) -> None:
        token_hash = hash_token(refresh_token)
        session = self._get_session_by_refresh_hash(token_hash)
        if session and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            self._save_session(session)
            log_event("auth.logout", user_id=session.user_id)

    def get_current_user(self, access_token: str) -> AuthenticatedUser:
        payload = decode_jwt(access_token, self.settings.jwt_secret)
        user_id = cast(str, payload["sub"])
        user = self._get_user(user_id)
        session_id = cast(str, payload.get("sid"))
        session = self._get_session(session_id)
        if session is None or session.revoked_at is not None or session.expires_at < datetime.now(timezone.utc):
            raise ValueError("invalid session")
        return AuthenticatedUser(user=user, memberships=self._user_memberships(user.id))

    def me(self, access_token: str) -> dict:
        current = self.get_current_user(access_token)
        active_membership = next((m for m in current.memberships if m.active), None)
        return {
            "user": self._serialize_user(current.user),
            "memberships": [self._serialize_membership(m) for m in current.memberships],
            "active_organization": {"id": active_membership.organization.id, "name": active_membership.organization.name, "slug": active_membership.organization.slug} if active_membership else None,
            "active_permissions": _permissions_for_role(active_membership.role) if active_membership else [],
        }
