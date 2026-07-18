"""pagination indexes for incidents and evidence

Revision ID: 0011_pagination_indexes
Revises: 0010_edge_worker_telemetry
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_pagination_indexes"
down_revision = "0010_edge_worker_telemetry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_incidents_org_created_id", "incidents", ["organization_id", "created_at", "id"])
    op.create_index("ix_incidents_org_status_created_id", "incidents", ["organization_id", "status", "created_at", "id"])
    op.create_index("ix_incidents_org_site_created_id", "incidents", ["organization_id", "site_id", "created_at", "id"])
    op.create_index("ix_incidents_org_camera_created_id", "incidents", ["organization_id", "camera_id", "created_at", "id"])
    op.create_index("ix_incidents_org_zone_created_id", "incidents", ["organization_id", "zone_id", "created_at", "id"])
    op.create_index("ix_incidents_org_severity_created_id", "incidents", ["organization_id", "severity", "created_at", "id"])
    op.create_index("ix_evidence_metadata_org_created_id", "evidence_metadata", ["organization_id", "created_at", "id"])
    op.create_index("ix_evidence_metadata_org_incident_created_id", "evidence_metadata", ["organization_id", "incident_id", "created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_metadata_org_incident_created_id", table_name="evidence_metadata")
    op.drop_index("ix_evidence_metadata_org_created_id", table_name="evidence_metadata")
    op.drop_index("ix_incidents_org_severity_created_id", table_name="incidents")
    op.drop_index("ix_incidents_org_zone_created_id", table_name="incidents")
    op.drop_index("ix_incidents_org_camera_created_id", table_name="incidents")
    op.drop_index("ix_incidents_org_site_created_id", table_name="incidents")
    op.drop_index("ix_incidents_org_status_created_id", table_name="incidents")
    op.drop_index("ix_incidents_org_created_id", table_name="incidents")
