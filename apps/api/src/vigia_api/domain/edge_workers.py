from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


class EdgeWorkerStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


@dataclass
class EdgeWorker:
    id: str
    organization_id: str
    site_id: str
    name: str
    client_id: str
    api_key_hash: str
    allowed_camera_ids: list[str] = field(default_factory=list)
    status: EdgeWorkerStatus = EdgeWorkerStatus.ACTIVE
    last_heartbeat_at: datetime | None = None
    # Último `status` recebido no heartbeat: latência, fila, último erro e as regras que o
    # modelo não consegue avaliar. Sem isto, "zero incidentes" parece conformidade quando
    # pode ser cegueira do modelo.
    last_telemetry: dict | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
