from dataclasses import dataclass
import os


@dataclass(frozen=True)
class WorkerConfig:
    edge_worker_id: str
    organization_id: str
    site_id: str
    camera_id: str
    zone_id: str
    worker_version: str = "0.1.0"
    contract_version: str = "v1"
    edge_api_base_url: str | None = None
    edge_client_id: str | None = None
    edge_api_key: str | None = None
    cv_mode: str = "mock"
    cv_real_enabled: bool = False
    cv_real_marker: str | None = None
    cv_real_model_version: str = "real-cv-0"
    cv_model_path: str | None = None
    cv_confidence_threshold: float = 0.4
    edge_source_type: str = "mock"
    edge_source_uri: str | None = None
    edge_video_frame_stride: int = 15
    edge_reconnect_backoff_seconds: float = 2.0
    edge_reconnect_max_backoff_seconds: float = 30.0
    edge_frame_interval_seconds: float = 0.0
    edge_max_frames: int | None = None
    edge_detection_cooldown_seconds: int = 0
    edge_buffer_path: str | None = None
    edge_buffer_max_attempts: int = 5
    edge_buffer_backoff_seconds: float = 1.0
    run_once: bool = False
    poll_interval_seconds: int = 30


def default_config() -> WorkerConfig:
    return WorkerConfig(
        edge_worker_id="edge-worker-001",
        organization_id="org-demo",
        site_id="site-demo",
        camera_id="camera-demo-01",
        zone_id="zone-demo-01",
        edge_api_base_url=os.environ.get("EDGE_API_BASE_URL"),
        edge_client_id=os.environ.get("EDGE_CLIENT_ID"),
        edge_api_key=os.environ.get("EDGE_API_KEY"),
        cv_mode=os.environ.get("CV_MODE", "mock"),
        cv_real_enabled=os.environ.get("CV_REAL_ENABLED", "false").lower() in {"1", "true", "yes"},
        cv_real_marker=os.environ.get("CV_REAL_MARKER"),
        cv_real_model_version=os.environ.get("CV_REAL_MODEL_VERSION", "real-cv-0"),
        cv_model_path=os.environ.get("CV_MODEL_PATH"),
        cv_confidence_threshold=float(os.environ.get("CV_CONFIDENCE_THRESHOLD", "0.4")),
        edge_source_type=os.environ.get("EDGE_SOURCE_TYPE", "mock"),
        edge_source_uri=os.environ.get("EDGE_SOURCE_URI"),
        edge_video_frame_stride=int(os.environ.get("EDGE_VIDEO_FRAME_STRIDE", "15")),
        edge_reconnect_backoff_seconds=float(os.environ.get("EDGE_RECONNECT_BACKOFF_SECONDS", "2")),
        edge_reconnect_max_backoff_seconds=float(os.environ.get("EDGE_RECONNECT_MAX_BACKOFF_SECONDS", "30")),
        edge_frame_interval_seconds=float(os.environ.get("EDGE_FRAME_INTERVAL_SECONDS", "0")),
        edge_max_frames=int(os.environ["EDGE_MAX_FRAMES"]) if os.environ.get("EDGE_MAX_FRAMES") else None,
        edge_detection_cooldown_seconds=int(os.environ.get("EDGE_DETECTION_COOLDOWN_SECONDS", "0")),
        edge_buffer_path=os.environ.get("EDGE_BUFFER_PATH"),
        edge_buffer_max_attempts=int(os.environ.get("EDGE_BUFFER_MAX_ATTEMPTS", "5")),
        edge_buffer_backoff_seconds=float(os.environ.get("EDGE_BUFFER_BACKOFF_SECONDS", "1.0")),
        run_once=os.environ.get("EDGE_RUN_ONCE", "false").lower() in {"1", "true", "yes"},
        poll_interval_seconds=int(os.environ.get("EDGE_POLL_INTERVAL_SECONDS", "30")),
    )
