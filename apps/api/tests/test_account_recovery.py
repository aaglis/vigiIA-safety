import unittest
from datetime import datetime, timedelta, timezone

from vigia_api.domain.auth import User, UserSession
from vigia_api.services.account_recovery import AccountRecoveryService
from vigia_api.services.auth import InMemoryAuthRepository
from vigia_api.services.security import hash_password, hash_token


class AccountRecoveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = InMemoryAuthRepository()
        self.user = User(id="user-1", email="alice@vigia.local", full_name="Alice", password_hash=hash_password("oldpass"))
        self.repo.add_user(self.user)
        self.repo.seed_demo_user()
        self.repo.sessions["sess-1"] = UserSession(id="sess-1", user_id="user-1", refresh_token_hash="x", expires_at=datetime.now(timezone.utc))
        self.service = AccountRecoveryService(self.repo)

    def test_generic_request_unknown_email(self) -> None:
        result = self.service.request_password_reset("missing@vigia.local", ip="1.2.3.4")
        self.assertIn("message", result)
        self.assertEqual(len(self.service.repository.password_resets), 0)

    def test_reset_token_hash_and_expiry(self) -> None:
        self.service.request_password_reset("alice@vigia.local")
        token = next(iter(self.service.repository.password_resets.values()))
        self.assertNotIn("oldpass", token.token_hash)
        self.assertGreaterEqual((token.expires_at - datetime.now(timezone.utc)).total_seconds(), 15 * 60 - 5)

    def test_confirm_rewrites_password_and_revokes_sessions(self) -> None:
        self.service.request_password_reset("alice@vigia.local")
        raw = self.service.repository.emails[-1].body.split(": ", 1)[1]
        old_hash = self.user.password_hash
        updated = self.service.confirm_password_reset(raw, "newpass")
        self.assertNotEqual(updated.password_hash, old_hash)
        self.assertIsNotNone(self.repo.sessions["sess-1"].revoked_at)
        with self.assertRaises(ValueError):
            self.service.confirm_password_reset(raw, "another")

    def test_expired_token_fails(self) -> None:
        self.service.request_password_reset("alice@vigia.local")
        token = next(iter(self.service.repository.password_resets.values()))
        token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        raw = self.service.repository.emails[-1].body.split(": ", 1)[1]
        with self.assertRaises(ValueError):
            self.service.confirm_password_reset(raw, "newpass")

    def test_email_verification_sets_verified_and_cannot_reuse(self) -> None:
        raw = self.service.create_email_verification(email="alice@vigia.local")
        user = self.service.verify_email(raw)
        self.assertIsNotNone(user.email_verified_at)
        with self.assertRaises(ValueError):
            self.service.verify_email(raw)

    def test_audit_and_queue_no_raw_token_in_audit(self) -> None:
        self.service.request_password_reset("alice@vigia.local")
        self.assertTrue(self.service.repository.emails)
        self.assertTrue(self.service.repository.audit_logs)
        self.assertFalse(any("Reset token" in str(log.metadata) for log in self.service.repository.audit_logs))


if __name__ == "__main__":
    unittest.main()
