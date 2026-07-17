"""password reset and email verification tokens

Revision ID: 0008_account_recovery_tokens
Revises: 0007_organization_plan_owner
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_account_recovery_tokens"
down_revision = "0007_organization_plan_owner"
branch_labels = None
depends_on = None


def _token_table(name: str, *, with_revoked: bool) -> None:
    columns = [
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    ]
    if with_revoked:
        columns.append(sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(name, *columns)
    op.create_index(f"ix_{name}_user_id", name, ["user_id"])
    op.create_index(f"ix_{name}_token_hash", name, ["token_hash"])
    op.create_index(f"ix_{name}_status", name, ["status"])


def upgrade() -> None:
    _token_table("password_reset_tokens", with_revoked=True)
    _token_table("email_verification_tokens", with_revoked=False)


def downgrade() -> None:
    for name in ("email_verification_tokens", "password_reset_tokens"):
        op.drop_index(f"ix_{name}_status", table_name=name)
        op.drop_index(f"ix_{name}_token_hash", table_name=name)
        op.drop_index(f"ix_{name}_user_id", table_name=name)
        op.drop_table(name)
