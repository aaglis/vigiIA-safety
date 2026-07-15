"""auth session context fields

Revision ID: 0003_auth_session_ctx
Revises: 0002_incident_idempotency
Create Date: 2026-07-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_auth_session_ctx"
down_revision = "0002_incident_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_sessions", sa.Column("user_agent", sa.Text(), nullable=True))
    op.add_column("user_sessions", sa.Column("ip_address", sa.String(length=64), nullable=True))
    op.add_column("user_sessions", sa.Column("active_organization_id", sa.String(length=36), nullable=True))


def downgrade() -> None:
    op.drop_column("user_sessions", "active_organization_id")
    op.drop_column("user_sessions", "ip_address")
    op.drop_column("user_sessions", "user_agent")
