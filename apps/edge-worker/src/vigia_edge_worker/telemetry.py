from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field
from statistics import mean
from typing import Any
from urllib.parse import urlparse, urlunparse


LATENCY_WINDOW = 500


def sanitize_error(value: object) -> str:
    text = str(value)
    lowered = text.lower()
    if any(marker in lowered for marker in ("api_key", "apikey", "token", "password", "secret")):
        return "***"
    if "://" in text:
        parsed = urlparse(text)
        if parsed.scheme and (parsed.username or parsed.password):
            netloc = parsed.hostname or ""
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"
            if parsed.username:
                netloc = f"{parsed.username}:***@{netloc}" if parsed.password else f"{parsed.username}@{netloc}"
            elif parsed.password:
                netloc = f":***@{netloc}"
            text = urlunparse((parsed.scheme, netloc, parsed.path or "", parsed.params or "", parsed.query or "", parsed.fragment or ""))
    return text[:180]


@dataclass
class TelemetryState:
    cv_mode: str
    source_type: str
    worker_version: str
    processed_frames: int = 0
    emitted_events: int = 0
    buffered_events: int = 0
    api_errors: int = 0
    source_errors: int = 0
    pending_queue: int = 0
    # Janela móvel: câmera ao vivo processa frames para sempre, então guardar toda
    # latência vazaria memória e faria a média valer "desde o boot" em vez de "agora".
    inference_latencies_ms: deque[float] = field(default_factory=lambda: deque(maxlen=LATENCY_WINDOW))
    send_latencies_ms: deque[float] = field(default_factory=lambda: deque(maxlen=LATENCY_WINDOW))
    last_error: str | None = None
    last_result: str | None = None
    # Regras que o modelo carregado NÃO consegue avaliar (ex.: EPI sem classe de capacete).
    # Vai no heartbeat: o operador precisa saber que a regra está inativa, e não confundir
    # "nenhum incidente" com "tudo certo".
    inactive_rules: list[str] = field(default_factory=list)

    def record_inference_latency(self, value_ms: float) -> None:
        self.inference_latencies_ms.append(value_ms)

    def record_send_latency(self, value_ms: float) -> None:
        self.send_latencies_ms.append(value_ms)

    def record_error(self, error: object, *, kind: str = "api") -> None:
        self.last_error = sanitize_error(error)
        if kind == "api" or kind == "buffer":
            self.api_errors += 1
        else:
            self.source_errors += 1

    def snapshot(self) -> dict[str, Any]:
        return {
            "cv_mode": self.cv_mode,
            "source_type": self.source_type,
            "worker_version": self.worker_version,
            "processed_frames": self.processed_frames,
            "emitted_events": self.emitted_events,
            "buffered_events": self.buffered_events,
            "api_errors": self.api_errors,
            "source_errors": self.source_errors,
            "pending_queue": self.pending_queue,
            "avg_inference_latency_ms": round(mean(self.inference_latencies_ms), 4) if self.inference_latencies_ms else 0.0,
            "avg_send_latency_ms": round(mean(self.send_latencies_ms), 4) if self.send_latencies_ms else 0.0,
            "inactive_rules": list(self.inactive_rules),
            "last_error": self.last_error,
            "last_result": self.last_result,
        }


def structured_log(event: str, **fields: Any) -> dict[str, Any]:
    payload = {"event": event, **{k: (sanitize_error(v) if k.endswith("error") or k in {"request_id", "correlation_id", "upload_path", "source_path"} else v) for k, v in fields.items() if v is not None}}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return payload
