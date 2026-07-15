"""incident detection idempotency

Revision ID: 0002_incident_idempotency
Revises: 0001_initial_persistent_schema
Create Date: 2026-07-13
"""

from __future__ import annotations

from alembic import op


revision = "0002_incident_idempotency"
down_revision = "0001_initial_persistent_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_incidents_org_detection_event", "incidents", ["organization_id", "detection_event_id"])


def downgrade() -> None:
    op.drop_constraint("uq_incidents_org_detection_event", "incidents", type_="unique")
