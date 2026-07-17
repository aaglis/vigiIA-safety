"""organization plan and creator

Revision ID: 0007_organization_plan_owner
Revises: 0006_invites
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_organization_plan_owner"
down_revision = "0006_invites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("plan", sa.String(length=64), nullable=True))
    op.add_column("organizations", sa.Column("created_by_user_id", sa.String(length=36), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "created_by_user_id")
    op.drop_column("organizations", "plan")
