from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    from sqlalchemy import select  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    select = None  # type: ignore[assignment]

from ..domain.account_recovery import EmailVerificationToken, PasswordResetToken, QueuedRecoveryEmail, RecoveryAuditLog, RecoveryTokenStatus
from .models import EmailVerificationToken as EmailVerificationRow
from .models import PasswordResetToken as PasswordResetRow


class SqlAlchemyAccountRecoveryRepository:
    """Tokens de reset/verificação persistidos. Fila de e-mail e audit seguem em memória
    (ver knownLimitations): o envio real é responsabilidade do notifier."""

    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory
        self.emails: list[QueuedRecoveryEmail] = []
        self.audit_logs: list[RecoveryAuditLog] = []

    def _aware(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    def _reset_to_domain(self, row: PasswordResetRow | None) -> PasswordResetToken | None:
        if row is None:
            return None
        return PasswordResetToken(id=row.id, user_id=row.user_id, email=row.email, token_hash=row.token_hash, status=RecoveryTokenStatus(row.status), expires_at=self._aware(row.expires_at), created_at=self._aware(row.created_at), used_at=self._aware(row.used_at), revoked_at=self._aware(row.revoked_at))

    def _verification_to_domain(self, row: EmailVerificationRow | None) -> EmailVerificationToken | None:
        if row is None:
            return None
        return EmailVerificationToken(id=row.id, user_id=row.user_id, email=row.email, token_hash=row.token_hash, status=RecoveryTokenStatus(row.status), expires_at=self._aware(row.expires_at), created_at=self._aware(row.created_at), used_at=self._aware(row.used_at))

    def save_password_reset(self, token: PasswordResetToken) -> None:
        with self.session_factory() as session:
            session.merge(PasswordResetRow(id=token.id, user_id=token.user_id, email=token.email, token_hash=token.token_hash, status=token.status.value, expires_at=token.expires_at, created_at=token.created_at, used_at=token.used_at, revoked_at=token.revoked_at))
            session.commit()

    def find_password_reset_by_token_hash(self, token_hash: str) -> PasswordResetToken | None:
        if select is None:
            return None
        with self.session_factory() as session:
            row = session.execute(select(PasswordResetRow).where(PasswordResetRow.token_hash == token_hash)).scalars().first()
            return self._reset_to_domain(row)

    def save_email_verification(self, token: EmailVerificationToken) -> None:
        with self.session_factory() as session:
            session.merge(EmailVerificationRow(id=token.id, user_id=token.user_id, email=token.email, token_hash=token.token_hash, status=token.status.value, expires_at=token.expires_at, created_at=token.created_at, used_at=token.used_at))
            session.commit()

    def find_email_verification_by_token_hash(self, token_hash: str) -> EmailVerificationToken | None:
        if select is None:
            return None
        with self.session_factory() as session:
            row = session.execute(select(EmailVerificationRow).where(EmailVerificationRow.token_hash == token_hash)).scalars().first()
            return self._verification_to_domain(row)

    def queue_email(self, email: QueuedRecoveryEmail) -> None:
        self.emails.append(email)

    def add_audit(self, entry: Any) -> None:
        self.audit_logs.append(entry)
