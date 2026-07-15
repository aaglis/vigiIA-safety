from .config import WorkerConfig
from .detector import DetectionResult, Detector, FrameInput
from .events import DetectionEvent, new_event_id, utc_now


class MockDetector:
    def __init__(self, config: WorkerConfig) -> None:
        self.config = config

    def detect(self, frame: FrameInput) -> list[DetectionResult]:
        return [DetectionResult(event_type="mock_detection", confidence=0.92, model_version="mock-vision-0", zone_id=self.config.zone_id, evidence={"track_id": "track-001"}, metadata={"cv_mode": "mock"})]


def detect_once(config: WorkerConfig) -> DetectionEvent:
    return DetectionEvent(
        event_id=new_event_id(),
        camera_id=config.camera_id,
        site_id=config.site_id,
        organization_id=config.organization_id,
        timestamp=utc_now(),
        event_type="mock_detection",
        zone_id=config.zone_id,
        confidence=0.92,
        model_version="mock-vision-0",
        worker_id=config.edge_worker_id,
        evidence={"track_id": "track-001"},
    )
