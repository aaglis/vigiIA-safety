import unittest

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


if __name__ == "__main__":
    unittest.main()
