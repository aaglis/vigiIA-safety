"""guarda a última telemetria do heartbeat do worker

A tabela só tinha `status` e `last_heartbeat_at`: todo o payload do heartbeat — latência
de inferência, fila pendente, último erro e as regras que o modelo não consegue avaliar
(`inactive_rules`) — era descartado silenciosamente. Sem isso, "zero incidentes de EPI"
parece conformidade quando na verdade o modelo não enxerga capacete, e diagnosticar um
worker em campo exige entrar no container.

Guarda só a ÚLTIMA telemetria (sem histórico): o valor é saber o estado agora, e série
temporal cresceria sem limite sem ninguém ter pedido.

Revision ID: 0010_edge_worker_telemetry
Revises: 0009_zone_name
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_edge_worker_telemetry"
down_revision = "0009_zone_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("edge_workers", sa.Column("last_telemetry_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("edge_workers", "last_telemetry_json")
