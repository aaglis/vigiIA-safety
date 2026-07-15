from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class DetectionEvent:
    event_id: str
    camera_id: str
    site_id: str
    organization_id: str
    timestamp: str
    event_type: str
    zone_id: str
    confidence: float
    model_version: str
    worker_id: str | None = None
    evidence: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data["worker_id"] is None:
            data.pop("worker_id")
        if data["evidence"] is None:
            data.pop("evidence")
        if data.get("metadata") is None:
            data.pop("metadata", None)
        return data


@dataclass(frozen=True)
class HeartbeatEvent:
    client_id: str
    organization_id: str
    site_id: str
    sent_at: str
    status: dict[str, Any]
    version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_event_id() -> str:
    return str(uuid4())


def validate_detection_event(payload: dict[str, Any]) -> None:
    required = {"event_id", "camera_id", "site_id", "organization_id", "timestamp", "event_type", "zone_id", "confidence", "model_version"}
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"missing detection fields: {', '.join(missing)}")
    allowed = required | {"worker_id", "evidence", "metadata", "severity", "summary"}
    extra = sorted(set(payload) - allowed)
    if extra:
        raise ValueError(f"unexpected detection fields: {', '.join(extra)}")


def validate_heartbeat_event(payload: dict[str, Any]) -> None:
    required = {"client_id", "organization_id", "site_id", "sent_at", "status"}
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"missing heartbeat fields: {', '.join(missing)}")
    allowed = required | {"version"}
    extra = sorted(set(payload) - allowed)
    if extra:
        raise ValueError(f"unexpected heartbeat fields: {', '.join(extra)}")
