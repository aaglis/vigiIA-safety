from .config import WorkerConfig
from .events import HeartbeatEvent, utc_now
from .telemetry import TelemetryState


def build_heartbeat(config: WorkerConfig, processed_frames: int, emitted_events: int, status: str = "ok", telemetry: TelemetryState | None = None, last_error: str | None = None, pending_queue: int | None = None) -> HeartbeatEvent:
    extra = telemetry.snapshot() if telemetry is not None else {}
    if last_error is not None:
        extra["last_error"] = last_error
    if pending_queue is not None:
        extra["pending_queue"] = pending_queue
    extra.update({"state": status, "processed_frames": processed_frames, "emitted_events": emitted_events})
    return HeartbeatEvent(
        client_id=config.edge_worker_id,
        organization_id=config.organization_id,
        site_id=config.site_id,
        sent_at=utc_now(),
        status=extra,
        version=config.contract_version,
    )
