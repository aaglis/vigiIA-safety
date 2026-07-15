from __future__ import annotations

from dataclasses import dataclass

from .config import WorkerConfig
from .detector import Detector
from .mock_detector import MockDetector
from .real_detector import RealDetector, RealDetectorConfig, RealDetectorError


@dataclass(frozen=True)
class DetectorSelection:
    cv_mode: str = "mock"
    cv_real_enabled: bool = False
    cv_real_marker: str | None = None
    cv_real_model_version: str = "real-cv-0"


def build_detector(config: WorkerConfig, selection: DetectorSelection | None = None) -> Detector:
    selection = selection or DetectorSelection(cv_mode=config.cv_mode, cv_real_enabled=config.cv_real_enabled, cv_real_marker=config.cv_real_marker, cv_real_model_version=config.cv_real_model_version)
    if selection.cv_mode == "mock":
        return MockDetector(config)
    if selection.cv_mode == "real":
        return RealDetector(config, RealDetectorConfig(enabled=selection.cv_real_enabled, marker=selection.cv_real_marker, model_version=selection.cv_real_model_version))
    raise ValueError("CV_MODE must be mock or real")
