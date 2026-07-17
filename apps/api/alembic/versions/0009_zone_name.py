"""zona ganha nome legível

A zona só tinha id (`zone-demo-01`), então a UI e o alerta mostravam o id cru para o
operador. Quem cadastra precisa nomear a área como ela é conhecida na planta ("Porta da
Doca", "Linha de Pintura") — é isso que faz o incidente significar algo.

Backfill: zonas existentes recebem um nome derivado do tipo, para nenhuma ficar sem rótulo.

Revision ID: 0009_zone_name
Revises: 0008_account_recovery_tokens
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_zone_name"
down_revision = "0008_account_recovery_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("zones", sa.Column("name", sa.String(length=120), nullable=True))
    op.execute(
        """
        UPDATE zones SET name = CASE zone_type
            WHEN 'restricted' THEN 'Área restrita'
            WHEN 'ppe' THEN 'Área de EPI'
            WHEN 'access' THEN 'Área de acesso'
            ELSE 'Zona'
        END
        WHERE name IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("zones", "name")
