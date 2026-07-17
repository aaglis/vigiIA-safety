from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class FrameInput:
    camera_id: str
    site_id: str
    organization_id: str
    timestamp: str
    worker_id: str | None = None
    image_bytes: bytes | None = None
    # Frame decodificado (ndarray BGR) + dimensões, quando a fonte é vídeo/RTSP.
    # `Any` para não obrigar numpy quando a CV real não está instalada.
    frame: Any = None
    width: int | None = None
    height: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DetectionResult:
    event_type: str
    confidence: float
    model_version: str
    zone_id: str
    evidence: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    # JPEG já anotado com as caixas (bytes) para virar a evidência enviada. Não serializado no evento.
    annotated_jpeg: bytes | None = None


class Detector(Protocol):
    def detect(self, frame: FrameInput) -> list[DetectionResult]:
        ...
