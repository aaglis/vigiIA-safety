from __future__ import annotations

from dataclasses import dataclass

from .config import WorkerConfig
from .detector import DetectionResult, Detector, FrameInput


@dataclass(frozen=True)
class RealDetectorConfig:
    enabled: bool = False
    marker: str | None = None
    model_version: str = "real-cv-0"


class RealDetectorError(RuntimeError):
    pass


class RealDetector:
    def __init__(self, config: WorkerConfig, real_config: RealDetectorConfig | None = None) -> None:
        self.config = config
        self.real_config = real_config or RealDetectorConfig()

    def detect(self, frame: FrameInput) -> list[DetectionResult]:
        if not self.real_config.enabled:
            raise RealDetectorError("real detector disabled: set CV_REAL_ENABLED=1")
        if not frame.image_bytes:
            raise RealDetectorError("real detector requires image_bytes frame input")
        marker = self.real_config.marker or frame.metadata.get("cv_marker")
        if not marker:
            raise RealDetectorError("real detector requires CV_REAL_MARKER or frame.metadata.cv_marker")
        if marker.encode("utf-8") not in frame.image_bytes:
            return []
        return [
            DetectionResult(
                event_type="real_detection",
                confidence=0.98,
                model_version=self.real_config.model_version,
                zone_id=self.config.zone_id,
                evidence={"marker": marker},
                metadata={"cv_mode": "real", "source": "local-frame"},
            )
        ]
