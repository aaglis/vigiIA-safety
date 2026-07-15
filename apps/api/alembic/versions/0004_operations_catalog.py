"""operations catalog tables

Revision ID: 0004_operations_catalog
Revises: 0003_auth_session_ctx
Create Date: 2026-07-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_operations_catalog"
down_revision = "0003_auth_session_ctx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sites_organization_id", "sites", ["organization_id"])
    op.create_table(
        "departments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_departments_organization_id", "departments", ["organization_id"])
    op.create_index("ix_departments_site_id", "departments", ["site_id"])
    op.create_table(
        "workers",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("internal_id", sa.String(length=255), nullable=False),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=True),
        sa.Column("department_id", sa.String(length=36), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("contact", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workers_organization_id", "workers", ["organization_id"])
    op.create_table(
        "cameras",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("stream_identifier", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cameras_organization_id", "cameras", ["organization_id"])
    op.create_index("ix_cameras_site_id", "cameras", ["site_id"])
    op.create_table(
        "zones",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("camera_id", sa.String(length=36), sa.ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_type", sa.String(length=32), nullable=False),
        sa.Column("polygon_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_zones_organization_id", "zones", ["organization_id"])
    op.create_index("ix_zones_site_id", "zones", ["site_id"])
    op.create_index("ix_zones_camera_id", "zones", ["camera_id"])
    op.create_table(
        "safety_rules",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=True),
        sa.Column("zone_id", sa.String(length=36), sa.ForeignKey("zones.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_safety_rules_organization_id", "safety_rules", ["organization_id"])
    op.create_index("ix_safety_rules_site_id", "safety_rules", ["site_id"])
    op.create_index("ix_safety_rules_zone_id", "safety_rules", ["zone_id"])
    op.create_table(
        "required_ppe",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", sa.String(length=36), sa.ForeignKey("safety_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("site_id", sa.String(length=36), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=True),
        sa.Column("zone_id", sa.String(length=36), sa.ForeignKey("zones.id", ondelete="CASCADE"), nullable=True),
        sa.Column("item", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_required_ppe_organization_id", "required_ppe", ["organization_id"])
    op.create_index("ix_required_ppe_rule_id", "required_ppe", ["rule_id"])
    op.create_index("ix_required_ppe_site_id", "required_ppe", ["site_id"])
    op.create_index("ix_required_ppe_zone_id", "required_ppe", ["zone_id"])


def downgrade() -> None:
    op.drop_index("ix_required_ppe_zone_id", table_name="required_ppe")
    op.drop_index("ix_required_ppe_site_id", table_name="required_ppe")
    op.drop_index("ix_required_ppe_rule_id", table_name="required_ppe")
    op.drop_index("ix_required_ppe_organization_id", table_name="required_ppe")
    op.drop_table("required_ppe")
    op.drop_index("ix_safety_rules_zone_id", table_name="safety_rules")
    op.drop_index("ix_safety_rules_site_id", table_name="safety_rules")
    op.drop_index("ix_safety_rules_organization_id", table_name="safety_rules")
    op.drop_table("safety_rules")
    op.drop_index("ix_zones_camera_id", table_name="zones")
    op.drop_index("ix_zones_site_id", table_name="zones")
    op.drop_index("ix_zones_organization_id", table_name="zones")
    op.drop_table("zones")
    op.drop_index("ix_cameras_site_id", table_name="cameras")
    op.drop_index("ix_cameras_organization_id", table_name="cameras")
    op.drop_table("cameras")
    op.drop_index("ix_workers_organization_id", table_name="workers")
    op.drop_table("workers")
    op.drop_index("ix_departments_site_id", table_name="departments")
    op.drop_index("ix_departments_organization_id", table_name="departments")
    op.drop_table("departments")
    op.drop_index("ix_sites_organization_id", table_name="sites")
    op.drop_table("sites")
