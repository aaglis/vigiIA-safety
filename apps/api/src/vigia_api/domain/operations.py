from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class EntityStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class ZoneType(StrEnum):
    ACCESS = "access"
    RESTRICTED = "restricted"
    PPE = "ppe"


@dataclass
class Site:
    id: str
    organization_id: str
    name: str
    address: str | None = None
    status: EntityStatus = EntityStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Department:
    id: str
    organization_id: str
    site_id: str
    name: str
    status: EntityStatus = EntityStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Worker:
    id: str
    organization_id: str
    name: str
    internal_id: str
    site_id: str | None = None
    department_id: str | None = None
    status: EntityStatus = EntityStatus.ACTIVE
    contact: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Camera:
    id: str
    organization_id: str
    site_id: str
    name: str
    stream_identifier: str
    status: EntityStatus = EntityStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Zone:
    id: str
    organization_id: str
    site_id: str
    camera_id: str
    zone_type: ZoneType
    polygon_json: dict[str, Any]
    status: EntityStatus = EntityStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SafetyRule:
    id: str
    organization_id: str
    site_id: str | None = None
    zone_id: str | None = None
    name: str = ""
    status: EntityStatus = EntityStatus.ACTIVE
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RequiredPPE:
    id: str
    organization_id: str
    rule_id: str
    site_id: str | None = None
    zone_id: str | None = None
    item: str = ""
    status: EntityStatus = EntityStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class OperationalAuditLog:
    id: str
    organization_id: str | None
    actor_user_id: str
    action: str
    target_type: str
    target_id: str
    ip: str | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Fontes de vídeo aceitas por uma câmera. Em produção a câmera é sempre um stream
# ao vivo (RTSP/RTMP); em dev aceitamos também um arquivo de vídeo, que faz o papel
# de "câmera" para validar a visão computacional em localhost.
VIDEO_STREAM_SUFFIXES = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")
LIVE_STREAM_SOURCE_TYPES = frozenset({"rtsp", "rtmp"})
STRICT_STREAM_ENVIRONMENTS = frozenset({"production", "staging"})


def classify_stream_source(stream_identifier: str) -> str | None:
    """Deriva o tipo de fonte a partir do identificador do stream, ou None se inválido."""
    value = (stream_identifier or "").strip()
    if not value:
        return None
    lowered = value.lower()
    path_part = lowered.rsplit("?", 1)[0].rsplit("#", 1)[0]
    if lowered.startswith("rtsp://"):
        return "rtsp"
    if lowered.startswith("rtmp://"):
        return "rtmp"
    if lowered.startswith(("http://", "https://")):
        return "video" if path_part.endswith(VIDEO_STREAM_SUFFIXES) else "http"
    if lowered.startswith("file://") or path_part.endswith(VIDEO_STREAM_SUFFIXES):
        return "video"
    return None


def validate_stream_identifier(stream_identifier: str, app_env: str) -> str:
    """Valida o stream por ambiente e devolve o source_type derivado.

    dev/test: aceita rtsp://, rtmp://, http(s):// ou arquivo de vídeo (.mp4/.mov/...).
    production/staging: exige uma câmera ao vivo (rtsp:// ou rtmp://).
    Levanta ValueError com mensagem de campo quando inválido.
    """
    source_type = classify_stream_source(stream_identifier)
    if source_type is None:
        raise ValueError(
            "stream_identifier inválido: use rtsp://, rtmp://, http(s):// ou um arquivo de vídeo (.mp4/.mov/…)"
        )
    if (app_env or "dev").lower() in STRICT_STREAM_ENVIRONMENTS and source_type not in LIVE_STREAM_SOURCE_TYPES:
        raise ValueError(
            "em produção o stream_identifier deve ser uma câmera ao vivo (rtsp:// ou rtmp://)"
        )
    return source_type
