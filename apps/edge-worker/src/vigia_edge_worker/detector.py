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
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DetectionResult:
    event_type: str
    confidence: float
    model_version: str
    zone_id: str
    evidence: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Detector(Protocol):
    def detect(self, frame: FrameInput) -> list[DetectionResult]:
        ...
