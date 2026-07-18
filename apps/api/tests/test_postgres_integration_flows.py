from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any, cast

from vigia_api.container import build_container
from vigia_api.domain.auth import PlatformRole, User
from vigia_api.domain.incidents import IncidentStatus, parse_detection_event
from vigia_api.persistence.base import Base
from vigia_api.services.security import hash_password
from vigia_api.settings import Settings

try:
    from sqlalchemy import create_engine

    SQLALCHEMY_AVAILABLE = True
except Exception:
    SQLALCHEMY_AVAILABLE = False


def _postgres_url() -> str | None:
    url = os.environ.get("POSTGRES_TEST_DATABASE_URL", "").strip()
    return url or None


def _is_postgres(url: str | None) -> bool:
    return bool(url) and url.startswith(("postgresql://", "postgresql+psycopg://", "postgres://"))


@unittest.skipUnless(SQLALCHEMY_AVAILABLE and _is_postgres(_postgres_url()), "POSTGRES_TEST_DATABASE_URL must point to Postgres")
class PostgresIntegrationFlowsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database_url = _postgres_url()
        assert cls.database_url is not None
        cls.repo_root = Path(__file__).resolve().parents[3]
        cls.engine = create_engine(cls.database_url, future=True)  # type: ignore[operator]
        env = os.environ.copy()
        env["DATABASE_URL"] = cls.database_url
        env["POSTGRES_TEST_DATABASE_URL"] = cls.database_url
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=cls.repo_root / "apps/api", env=env, check=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        config = Settings(database_url=self.database_url, repository_backend="postgres", app_env="test")
        self.container = cast(Any, build_container(config, repository_backend="postgres", seed_dev=False))
        self._reset_tables()

    def tearDown(self) -> None:
        self._reset_tables()
        session_factory = getattr(self.container, "session_factory", None)
        bind = getattr(session_factory, "bind", None)
        if bind is not None:
            bind.dispose()

    def _reset_tables(self) -> None:
        with self.engine.begin() as connection:
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())

    def test_invite_create_accept_and_login(self) -> None:
        auth = self.container.auth_repository
        platform = self.container.platform_admin_service
        invite = self.container.invite_service

        platform.auth_repository.add_user(User(id="platform-admin", email="owner@vigia.local", full_name="Owner", password_hash=hash_password("pw"), platform_role=PlatformRole.PLATFORM_OWNER))
        org = platform.create_organization(name="Acme", legal_name="Acme LTDA", tax_id="12.345.678/0001-90", created_by_user_id="platform-admin", leader_email="leader@acme.local", plan="pro")
        created, token = invite.create_invite(org.id, "new@acme.local", "org_admin", "platform-admin", "org_owner")
        user = invite.accept_invite(token, "new@acme.local", "New User", "pw123")
        tokens, _, me = self.container.auth_service.login(user.email, "pw123")
        accepted = invite.repository.get(created.id)

        self.assertIsNotNone(accepted)
        self.assertEqual(accepted.status.value, "accepted")
        self.assertTrue(tokens.access_token)
        self.assertEqual(me.user.email, "new@acme.local")
        self.assertGreaterEqual(len(auth.list_memberships(user.id)), 1)

    def test_reset_password_and_email_verification(self) -> None:
        auth = self.container.auth_repository
        recovery = self.container.account_recovery_service
        auth.add_user(User(id="user-1", email="alice@vigia.local", full_name="Alice", password_hash=hash_password("oldpass")))

        raw_reset = recovery.request_password_reset("alice@vigia.local")["message"]
        self.assertIn("reset", raw_reset.lower())
        raw_token = recovery.repository.emails[-1].body.split(": ", 1)[1]
        updated = recovery.confirm_password_reset(raw_token, "newpass")
        self.assertEqual(updated.email, "alice@vigia.local")
        verification = recovery.create_email_verification(email="alice@vigia.local")
        verified = recovery.verify_email(verification)
        self.assertIsNotNone(verified.email_verified_at)

    def test_platform_admin_create_suspend_and_reactivate_org(self) -> None:
        admin = User(id="platform-admin", email="owner@vigia.local", full_name="Owner", password_hash=hash_password("pw"), platform_role=PlatformRole.PLATFORM_OWNER)
        self.container.auth_repository.add_user(admin)
        org = self.container.platform_admin_service.create_organization(name="Acme", legal_name="Acme LTDA", tax_id="12.345.678/0001-90", created_by_user_id=admin.id, leader_email="leader@acme.local", plan="pro")
        suspended = self.container.platform_admin_service.suspend_organization(org.id, admin.id)
        reactivated = self.container.platform_admin_service.reactivate_organization(org.id, admin.id)
        self.assertEqual(suspended.status.value, "suspended")
        self.assertEqual(reactivated.status.value, "active")

    def test_incident_notification_persists_and_processes_status(self) -> None:
        admin = User(id="platform-admin", email="owner@vigia.local", full_name="Owner", password_hash=hash_password("pw"), platform_role=PlatformRole.PLATFORM_OWNER)
        self.container.auth_repository.add_user(admin)
        org = self.container.platform_admin_service.create_organization(name="Acme", legal_name="Acme LTDA", tax_id="12.345.678/0001-90", created_by_user_id=admin.id, leader_email="leader@acme.local", plan="pro")
        incident = self.container.incident_repository.create_from_detection(parse_detection_event({"organization_id": org.id, "camera_id": "cam-1", "zone_id": "zone-1", "severity": "high", "summary": "demo"}))
        queued = self.container.incident_repository.notifications(org.id, incident.id)
        self.assertTrue(queued)
        self.assertEqual(queued[0].status, "queued")
        processed = self.container.incident_repository.update_notification_status(queued[0].id, "sent")
        self.assertEqual(processed.status, "sent")
        self.assertEqual(self.container.incident_repository.get(org.id, incident.id).status, IncidentStatus.OPEN)


if __name__ == "__main__":
    unittest.main()
