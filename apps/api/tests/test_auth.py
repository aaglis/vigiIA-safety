import unittest

from vigia_api.domain.auth import MembershipSummary, OrganizationSummary
from vigia_api.security.permissions import ROLE_PERMISSIONS, role_permissions
from vigia_api.services.auth import AuthService
from vigia_api.services.security import hash_password, verify_password


class AuthTest(unittest.TestCase):
    def test_password_hash_and_verify(self) -> None:
        password_hash = hash_password("secret")
        self.assertTrue(verify_password("secret", password_hash))
        self.assertFalse(verify_password("wrong", password_hash))

    def test_login_refresh_logout_and_me(self) -> None:
        service = AuthService()
        tokens, session, me = service.login("admin@vigia.local", "change-me-dev")
        self.assertTrue(tokens.access_token)
        self.assertTrue(tokens.refresh_token)
        self.assertEqual(me.user.email, "admin@vigia.local")
        refreshed_tokens, refreshed_session, _ = service.refresh(tokens.refresh_token)
        self.assertIsNotNone(session.revoked_at)
        self.assertIsNotNone(refreshed_session)
        me_payload = service.me(refreshed_tokens.access_token)
        self.assertIn("memberships", me_payload)
        service.logout(refreshed_tokens.refresh_token)
        self.assertIsNotNone(refreshed_session.revoked_at)
        with self.assertRaises(ValueError):
            service.me(refreshed_tokens.access_token)
        self.assertIn("active_permissions", me_payload)

    def test_rotated_refresh_token_cannot_be_reused(self) -> None:
        service = AuthService()
        tokens, _, _ = service.login("admin@vigia.local", "change-me-dev")
        refreshed_tokens, _, _ = service.refresh(tokens.refresh_token)
        with self.assertRaises(ValueError):
            service.refresh(tokens.refresh_token)
        with self.assertRaises(ValueError):
            service.login("admin@vigia.local", "bad-password")
        self.assertTrue(refreshed_tokens.refresh_token)

    def test_login_and_me_do_not_expose_sensitive_fields(self) -> None:
        service = AuthService()
        tokens, _, _ = service.login("admin@vigia.local", "change-me-dev")
        login_payload = {"tokens": {"access_token": tokens.access_token, "token_type": tokens.token_type, "access_token_expires_in": tokens.access_token_expires_in}, "me": service.me(tokens.access_token), "user": "admin@vigia.local"}
        self.assertNotIn("refresh_token", login_payload["tokens"])
        self.assertNotIn("password_hash", login_payload["me"]["user"])
        self.assertNotIn("refresh_token_hash", login_payload["me"]["user"])
        self.assertNotIn("password_hash", login_payload["me"])

    def test_me_returns_full_permission_strings_for_active_membership(self) -> None:
        service = AuthService()
        tokens, _, _ = service.login("admin@vigia.local", "change-me-dev")
        me_payload = service.me(tokens.access_token)
        self.assertEqual(me_payload["active_permissions"], sorted(role_permissions("owner")))
        self.assertTrue(all(isinstance(item, str) for item in me_payload["active_permissions"]))
        self.assertEqual(len(me_payload["active_permissions"]), len(ROLE_PERMISSIONS["org_owner"]))

    def test_me_derives_permissions_from_role_not_stored_subset(self) -> None:
        org = OrganizationSummary(id="org-test", name="Org Test", slug="org-test")
        for role in ("org_owner", "org_admin", "manager", "auditor_viewer"):
            with self.subTest(role=role):
                service = AuthService()
                user = service.repository.get_user_by_email("admin@vigia.local")
                if user is None:
                    self.fail("demo user not seeded")
                service.repository.memberships[user.id] = [MembershipSummary(organization=org, role=role, permissions=["view_dashboard"], active=True)]

                tokens, _, _ = service.login("admin@vigia.local", "change-me-dev")
                me_payload = service.me(tokens.access_token)

                expected = sorted(role_permissions(role))
                self.assertEqual(me_payload["active_permissions"], expected)
                self.assertEqual(me_payload["memberships"][0]["permissions"], expected)


if __name__ == "__main__":
    unittest.main()
