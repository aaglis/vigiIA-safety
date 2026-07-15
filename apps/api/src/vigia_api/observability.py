from __future__ import annotations

import json
import logging
from collections import defaultdict
from contextvars import ContextVar, Token
from time import perf_counter
from typing import Any
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger("vigia_api.observability")
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
metrics = {
    "requests_total": defaultdict(int),
    "request_latency_ms": defaultdict(list),
    "detections": defaultdict(int),
    "incidents": defaultdict(int),
    "worker_offline": defaultdict(int),
}


def set_request_id(request_id: str | None, token: Token[str | None] | None = None) -> Token[str | None] | None:
    if token is not None:
        request_id_var.reset(token)
        return None
    return request_id_var.set(request_id)


def get_request_id() -> str | None:
    return request_id_var.get()


def observe_request(route: str, status_code: int, elapsed_ms: float) -> None:
    metrics["requests_total"][(route, status_code)] += 1
    metrics["request_latency_ms"][route].append(elapsed_ms)


def increment_metric(name: str, key: tuple | str = "default", amount: int = 1) -> None:
    metrics.setdefault(name, defaultdict(int))
    metrics[name][key] += amount


def _metric_key(value: Any) -> str:
    if isinstance(value, tuple):
        return "|".join(str(item) for item in value)
    return str(value)


def snapshot_metrics() -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "requests_total": {f"{route}|{status}": count for (route, status), count in metrics["requests_total"].items()},
        "request_latency_ms": {route: {"count": len(values), "avg": round(sum(values) / len(values), 2) if values else 0.0} for route, values in metrics["request_latency_ms"].items()},
    }
    for name, bucket in metrics.items():
        if name in {"requests_total", "request_latency_ms"}:
            continue
        snapshot[name] = {_metric_key(key): count for key, count in bucket.items()}
    return snapshot


def sanitize_for_log(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        if "://" in value:
            parsed = urlparse(value)
            if parsed.scheme and (parsed.password or parsed.username or parsed.query or parsed.fragment):
                netloc = parsed.hostname or ""
                if parsed.port:
                    netloc = f"{netloc}:{parsed.port}"
                if parsed.username:
                    netloc = f"{parsed.username}:***@{netloc}" if parsed.password else f"{parsed.username}@{netloc}"
                elif parsed.password:
                    netloc = f":***@{netloc}"
                query = "***" if parsed.query else ""
                fragment = "***" if parsed.fragment else ""
                return urlunparse((parsed.scheme, netloc, parsed.path or "", parsed.params or "", query, fragment))
        lowered = value.lower()
        if any(marker in lowered for marker in ("token", "secret", "password", "apikey", "api_key")):
            return "***"
        return value
    if isinstance(value, dict):
        return {k: "***" if any(marker in str(k).lower() for marker in ("token", "secret", "password", "apikey", "api_key", "signature")) else sanitize_for_log(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_for_log(v) for v in value]
    return value


def build_event(action: str, organization_id: str | None = None, incident_id: str | None = None, edge_worker_id: str | None = None, user_id: str | None = None, level: str = "info", **extra: Any) -> dict[str, Any]:
    payload = {
        "action": action,
        "level": level,
        "request_id": get_request_id(),
        "organization_id": organization_id,
        "incident_id": incident_id,
        "edge_worker_id": edge_worker_id,
        "user_id": user_id,
        "extra": sanitize_for_log(extra),
    }
    return {k: v for k, v in payload.items() if v is not None}


def log_event(action: str, organization_id: str | None = None, incident_id: str | None = None, edge_worker_id: str | None = None, user_id: str | None = None, level: str = "info", **extra: Any) -> dict[str, Any]:
    event = build_event(action, organization_id=organization_id, incident_id=incident_id, edge_worker_id=edge_worker_id, user_id=user_id, level=level, **extra)
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.log(log_level, json.dumps(event, sort_keys=True, ensure_ascii=False))
    return event
