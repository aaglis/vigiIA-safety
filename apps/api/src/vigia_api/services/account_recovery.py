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

    def save_password_reset(self, token: PasswordResetToken) -> None:
        self.password_resets[token.id] = token

    def find_password_reset_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        return next((t for t in self.password_resets.values() if t.token_hash == token_hash), None)

    def save_email_verification(self, token: EmailVerificationToken) -> None:
        self.email_verifications[token.id] = token

    def find_email_verification_by_token_hash(self, token_hash: str) -> EmailVerificationToken | None:
        return next((t for t in self.email_verifications.values() if t.token_hash == token_hash), None)

    def queue_email(self, email: QueuedRecoveryEmail) -> None:
        self.emails.append(email)

    def add_audit(self, entry: RecoveryAuditLog) -> None:
        self.audit_logs.append(entry)


class AccountRecoveryService:
    def __init__(self, auth_repository: Any | None = None, repository: Any | None = None) -> None:
        self.auth_repository = auth_repository or InMemoryAuthRepository()
        self.repository = repository or InMemoryAccountRecoveryRepository()

    def _require_user(self, user_id: str) -> User:
        user = self.auth_repository.get_user_by_id(user_id)
        if user is None:
            raise KeyError(user_id)
        return user

    def _audit(self, action: str, user_id: str | None, email: str | None, **metadata: str) -> None:
        self.repository.add_audit(RecoveryAuditLog(id=generate_token(), action=action, user_id=user_id, email=email, created_at=datetime.now(timezone.utc), metadata=metadata))

    def request_password_reset(self, email: str, ip: str | None = None) -> dict:
        user = self.auth_repository.get_user_by_email(email)
        if user:
            raw_token = generate_token(32)
            token = PasswordResetToken(id=generate_token(), user_id=user.id, email=user.email, token_hash=hash_token(raw_token), expires_at=datetime.now(timezone.utc) + timedelta(minutes=30))
            self.repository.save_password_reset(token)
            self.repository.queue_email(QueuedRecoveryEmail(id=generate_token(), to_email=user.email, subject="Password reset", body=f"Reset token: {raw_token}", purpose="password_reset", user_id=user.id))
            self._audit("password_reset.requested", user.id, user.email, ip=ip or "")
        else:
            self._audit("password_reset.requested", None, email.lower(), ip=ip or "")
        return {"message": "If the account exists, a reset link will be sent."}

    def confirm_password_reset(self, raw_token: str, new_password: str) -> User:
        token = self.repository.find_password_reset_by_token_hash(hash_token(raw_token))
        now = datetime.now(timezone.utc)
        if not token:
            raise ValueError("invalid token")
        if token.status != RecoveryTokenStatus.PENDING:
            raise ValueError("token not available")
        if token.expires_at < now:
            token.status = RecoveryTokenStatus.EXPIRED
            self.repository.save_password_reset(token)
            raise ValueError("token expired")
        user = self._require_user(token.user_id)
        # Persistir de verdade: mutar o objeto não grava no backend SQL.
        self.auth_repository.update_password_hash(user.id, hash_password(new_password))
        self.auth_repository.revoke_sessions_for_user(user.id)
        token.status = RecoveryTokenStatus.USED
        token.used_at = now
        self.repository.save_password_reset(token)
        self.repository.queue_email(QueuedRecoveryEmail(id=generate_token(), to_email=user.email, subject="Password changed", body="Your password has been updated.", purpose="password_reset_complete", user_id=user.id))
        self._audit("password_reset.completed", user.id, user.email)
        return user

    def create_email_verification(self, user_id: str | None = None, email: str | None = None) -> str:
        if email:
            user = self.auth_repository.get_user_by_email(email)
            if not user:
                raise ValueError("user not found")
        elif user_id:
            user = self._require_user(user_id)
        else:
            raise ValueError("user required")
        raw_token = generate_token(32)
        token = EmailVerificationToken(id=generate_token(), user_id=user.id, email=user.email, token_hash=hash_token(raw_token), expires_at=datetime.now(timezone.utc) + timedelta(minutes=60))
        self.repository.save_email_verification(token)
        self.repository.queue_email(QueuedRecoveryEmail(id=generate_token(), to_email=user.email, subject="Verify your email", body=f"Verification token: {raw_token}", purpose="email_verification", user_id=user.id))
        self._audit("email_verification.requested", user.id, user.email)
        return raw_token

    def verify_email(self, raw_token: str) -> User:
        token = self.repository.find_email_verification_by_token_hash(hash_token(raw_token))
        now = datetime.now(timezone.utc)
        if not token:
            raise ValueError("invalid token")
        if token.status != RecoveryTokenStatus.PENDING:
            raise ValueError("token not available")
        if token.expires_at < now:
            token.status = RecoveryTokenStatus.EXPIRED
            self.repository.save_email_verification(token)
            raise ValueError("token expired")
        user = self._require_user(token.user_id)
        self.auth_repository.mark_email_verified(user.id)
        token.status = RecoveryTokenStatus.USED
        token.used_at = now
        self.repository.save_email_verification(token)
        user = self._require_user(token.user_id)
        self._audit("email_verification.completed", user.id, user.email)
        return user
