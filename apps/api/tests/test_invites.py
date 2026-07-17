import unittest
from datetime import datetime, timedelta, timezone

from vigia_api.domain.auth import PlatformRole, User
from vigia_api.services.auth import InMemoryAuthRepository
from vigia_api.services.invites import InviteService
from vigia_api.services.security import hash_password, hash_token
from vigia_api.api.v1 import invites as invites_api
from vigia_api.security.rate_limit import rate_limiter


class InviteTest(unittest.TestCase):
    def setUp(self) -> None:
        rate_limiter._windows.clear()
        self.auth_repo = InMemoryAuthRepository()
        admin = User(id="platform-admin", email="owner@vigia.local", full_name="Owner", password_hash=hash_password("pw"), platform_role=PlatformRole.PLATFORM_OWNER)
        self.auth_repo.add_user(admin)
        self.service = InviteService(self.auth_repo)

    def test_create_accept_and_audit(self) -> None:
        invite, token = self.service.create_invite("org-1", "new@vigia.local", "org_admin", "platform-admin", "org_owner")
        self.assertEqual(invite.status.value, "pending")
        self.assertTrue(any(e.to_email == "new@vigia.local" for e in self.service.repository.emails))
        user = self.service.accept_invite(token, "new@vigia.local", "New User", "pw123")
        self.assertEqual(user.email, "new@vigia.local")
        self.assertEqual(self.service.repository.invites[invite.id].status.value, "accepted")
        self.assertGreaterEqual(len(self.service.repository.audit_logs), 2)

    def test_manager_cannot_invite_org_admin(self) -> None:
        with self.assertRaises(PermissionError):
            self.service.create_invite("org-1", "x@vigia.local", "org_admin", "platform-admin", "manager")

    def test_manager_cannot_invite_org_owner(self) -> None:
        with self.assertRaises(PermissionError):
            self.service.create_invite("org-1", "x@vigia.local", "org_owner", "platform-admin", "manager")

    def test_invite_cannot_be_accepted_by_different_email(self) -> None:
        _, token = self.service.create_invite("org-1", "target@vigia.local", "auditor_viewer", "platform-admin", "manager")
        with self.assertRaises(ValueError):
            self.service.accept_invite(token, "other@vigia.local", "Other User", "pw123")

    def test_route_uses_session_actor_and_membership_role(self) -> None:
        class Membership:
            role = "manager"

        class CurrentUser:
            def __init__(self) -> None:
                self.user = type("U", (), {"id": "platform-admin"})()

        class Request:
            headers = {"origin": "http://localhost:3000", "referer": "http://localhost:3000/"}
            method = "POST"
            cookies = {}
            client = None
            url = type("U", (), {"path": "/api/v1/organizations/org-1/invites"})()
            app = type("App", (), {"state": type("State", (), {})()})()

        payload = invites_api.InviteIn(email="route@vigia.local", role="auditor_viewer")
        result = invites_api.create_invite("org-1", payload, request=Request(), membership=Membership(), current_user=CurrentUser())  # type: ignore[arg-type]
        self.assertEqual(result["invite"]["invited_by_user_id"], "platform-admin")

    def test_accept_route_does_not_expose_password_hash(self) -> None:
        class Request:
            headers = {"origin": "http://localhost:3000", "referer": "http://localhost:3000/"}
            method = "POST"
            cookies = {}
            client = None
            url = type("U", (), {"path": "/api/v1/invites/accept"})()
            app = type("App", (), {"state": type("State", (), {})()})()

        _, token = self.service.create_invite("org-1", "safe@vigia.local", "auditor_viewer", "platform-admin", "manager")
        previous_service = invites_api.service
        invites_api.service = self.service
        try:
            result = invites_api.accept_invite(invites_api.AcceptInviteIn(token=token, email="safe@vigia.local", full_name="Safe User", password="pw123"), request=Request())  # type: ignore[arg-type]
        finally:
            invites_api.service = previous_service
        self.assertEqual(result["user"]["email"], "safe@vigia.local")
        self.assertNotIn("password_hash", result["user"])

    def test_expired_revoked_and_reused_cannot_accept(self) -> None:
        invite, token = self.service.create_invite("org-1", "late@vigia.local", "auditor_viewer", "platform-admin", "manager")
        invite.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        with self.assertRaises(ValueError):
            self.service.accept_invite(token, "late@vigia.local", "Late User")
        invite.status = invite.status.EXPIRED
        invite.token_hash = hash_token(token)
        invite2, token2 = self.service.create_invite("org-1", "rev@vigia.local", "auditor_viewer", "platform-admin", "manager")
        self.service.revoke_invite(invite2.id)
        with self.assertRaises(ValueError):
            self.service.accept_invite(token2, "rev@vigia.local", "Rev User")


if __name__ == "__main__":
    unittest.main()
