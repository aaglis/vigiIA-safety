from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .detector import DetectionResult, FrameInput


@dataclass(frozen=True)
class RuleContext:
    site_id: str
    allowed_camera_ids: list[str]
    zones: list[dict[str, Any]] = field(default_factory=list)
    safety_rules: list[dict[str, Any]] = field(default_factory=list)
    required_ppe: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class AppliedDetection:
    event_type: str
    severity: str
    summary: str
    zone_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


class DetectionCooldown:
    def __init__(self, cooldown_seconds: int = 0) -> None:
        self.cooldown_seconds = cooldown_seconds
        self._last_seen: dict[tuple[str, str, str], datetime] = {}

    def allow(self, camera_id: str, zone_id: str, event_type: str, timestamp: str) -> bool:
        if self.cooldown_seconds <= 0:
            return True
        current = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        key = (camera_id, zone_id, event_type)
        last = self._last_seen.get(key)
        if last is not None and (current - last).total_seconds() < self.cooldown_seconds:
            return False
        self._last_seen[key] = current
        return True


class RuleEngine:
    def __init__(self, cooldown_seconds: int = 0) -> None:
        self.cooldown = DetectionCooldown(cooldown_seconds=cooldown_seconds)
        self.contexts: dict[str, RuleContext] = {}

    def load_context(self, context: dict[str, Any]) -> None:
        self.contexts[str(context["site_id"])] = RuleContext(
            site_id=str(context["site_id"]),
            allowed_camera_ids=list(context.get("allowed_camera_ids") or []),
            zones=list(context.get("zones") or []),
            safety_rules=list(context.get("safety_rules") or []),
            required_ppe=list(context.get("required_ppe") or []),
        )

    def apply(self, frame: FrameInput, result: DetectionResult) -> AppliedDetection | None:
        ctx = self.contexts.get(frame.site_id)
        if ctx is not None and ctx.allowed_camera_ids and frame.camera_id not in ctx.allowed_camera_ids:
            raise PermissionError("camera not allowed by rule context")
        zone = next((z for z in (ctx.zones if ctx else []) if str(z.get("id")) == result.zone_id), None)
        severity = "medium"
        summary = f"Detection in zone {result.zone_id}"
        if zone is not None:
            zone_type = str(zone.get("zone_type") or "").lower()
            if zone_type == "restricted":
                severity = "high"
                summary = f"Restricted zone alert at {result.zone_id}"
            elif zone_type == "ppe":
                severity = "medium"
                summary = f"PPE rule check at {result.zone_id}"
            else:
                severity = "low"
                summary = f"Informational zone event at {result.zone_id}"
        elif result.event_type == "real_detection":
            severity = "high"
            summary = "Real detection event"
        if not self.cooldown.allow(frame.camera_id, result.zone_id, result.event_type, frame.timestamp):
            return None
        metadata = {"cv_mode": result.metadata.get("cv_mode", "mock"), "rule_context": bool(ctx is not None), **result.metadata}
        return AppliedDetection(event_type=result.event_type, severity=severity, summary=summary, zone_id=result.zone_id, metadata=metadata)
