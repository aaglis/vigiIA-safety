from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..domain.account_recovery import EmailVerificationToken, PasswordResetToken, QueuedRecoveryEmail, RecoveryAuditLog, RecoveryTokenStatus
from ..domain.auth import User
from typing import Any

from .auth import InMemoryAuthRepository
from .security import generate_token, hash_password, hash_token


class InMemoryAccountRecoveryRepository:
    def __init__(self) -> None:
        self.password_resets: dict[str, PasswordResetToken] = {}
        self.email_verifications: dict[str, EmailVerificationToken] = {}
        self.emails: list[QueuedRecoveryEmail] = []
        self.audit_logs: list[RecoveryAuditLog] = []


class AccountRecoveryService:
    def __init__(self, auth_repository: Any | None = None) -> None:
        self.auth_repository = auth_repository or InMemoryAuthRepository()
        self.repository = InMemoryAccountRecoveryRepository()

    def _audit(self, action: str, user_id: str | None, email: str | None, **metadata: str) -> None:
        self.repository.audit_logs.append(RecoveryAuditLog(id=generate_token(), action=action, user_id=user_id, email=email, created_at=datetime.now(timezone.utc), metadata=metadata))

    def request_password_reset(self, email: str, ip: str | None = None) -> dict:
        user = self.auth_repository.get_user_by_email(email)
        if user:
            raw_token = generate_token(32)
            token = PasswordResetToken(id=generate_token(), user_id=user.id, email=user.email, token_hash=hash_token(raw_token), expires_at=datetime.now(timezone.utc) + timedelta(minutes=30))
            self.repository.password_resets[token.id] = token
            self.repository.emails.append(QueuedRecoveryEmail(id=generate_token(), to_email=user.email, subject="Password reset", body=f"Reset token: {raw_token}", purpose="password_reset", user_id=user.id))
            self._audit("password_reset.requested", user.id, user.email, ip=ip or "")
        else:
            self._audit("password_reset.requested", None, email.lower(), ip=ip or "")
        return {"message": "If the account exists, a reset link will be sent."}

    def confirm_password_reset(self, raw_token: str, new_password: str) -> User:
        token = next((t for t in self.repository.password_resets.values() if t.token_hash == hash_token(raw_token)), None)
        now = datetime.now(timezone.utc)
        if not token:
            raise ValueError("invalid token")
        if token.status != RecoveryTokenStatus.PENDING:
            raise ValueError("token not available")
        if token.expires_at < now:
            token.status = RecoveryTokenStatus.EXPIRED
            raise ValueError("token expired")
        user = self.auth_repository.users[token.user_id]
        user.password_hash = hash_password(new_password)
        for session in self.auth_repository.sessions.values():
            if session.user_id == user.id and session.revoked_at is None:
                session.revoked_at = now
        token.status = RecoveryTokenStatus.USED
        token.used_at = now
        self.repository.emails.append(QueuedRecoveryEmail(id=generate_token(), to_email=user.email, subject="Password changed", body="Your password has been updated.", purpose="password_reset_complete", user_id=user.id))
        self._audit("password_reset.completed", user.id, user.email)
        return user

    def create_email_verification(self, user_id: str | None = None, email: str | None = None) -> str:
        if email:
            user = self.auth_repository.get_user_by_email(email)
            if not user:
                raise ValueError("user not found")
        elif user_id:
            user = self.auth_repository.users[user_id]
        else:
            raise ValueError("user required")
        raw_token = generate_token(32)
        token = EmailVerificationToken(id=generate_token(), user_id=user.id, email=user.email, token_hash=hash_token(raw_token), expires_at=datetime.now(timezone.utc) + timedelta(minutes=60))
        self.repository.email_verifications[token.id] = token
        self.repository.emails.append(QueuedRecoveryEmail(id=generate_token(), to_email=user.email, subject="Verify your email", body=f"Verification token: {raw_token}", purpose="email_verification", user_id=user.id))
        self._audit("email_verification.requested", user.id, user.email)
        return raw_token

    def verify_email(self, raw_token: str) -> User:
        token = next((t for t in self.repository.email_verifications.values() if t.token_hash == hash_token(raw_token)), None)
        now = datetime.now(timezone.utc)
        if not token:
            raise ValueError("invalid token")
        if token.status != RecoveryTokenStatus.PENDING:
            raise ValueError("token not available")
        if token.expires_at < now:
            token.status = RecoveryTokenStatus.EXPIRED
            raise ValueError("token expired")
        user = self.auth_repository.users[token.user_id]
        user.email_verified_at = now
        token.status = RecoveryTokenStatus.USED
        token.used_at = now
        self._audit("email_verification.completed", user.id, user.email)
        return user
