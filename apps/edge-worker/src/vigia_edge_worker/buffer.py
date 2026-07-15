from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


@dataclass
class BufferedDetection:
    event_id: str
    payload: dict[str, Any]
    attempts: int = 0
    status: str = "pending"
    next_attempt_at: str | None = None
    last_error: str | None = None


class DetectionBuffer:
    def __init__(self, base_path: str, *, max_attempts: int = 5, backoff_seconds: float = 1.0) -> None:
        self.root = Path(base_path)
        self.pending_dir = self.root / "pending"
        self.sent_dir = self.root / "sent"
        self.failed_dir = self.root / "failed"
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self.sent_dir.mkdir(parents=True, exist_ok=True)
        self.failed_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, state: str, event_id: str) -> Path:
        return self.root / state / f"{event_id}.json"

    def _atomic_write(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as tmp:
            json.dump(data, tmp, ensure_ascii=False, sort_keys=True)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp.name, path)

    def enqueue(self, payload: dict[str, Any]) -> BufferedDetection:
        event_id = str(payload["event_id"])
        record = BufferedDetection(event_id=event_id, payload=payload)
        self._atomic_write(self._path("pending", event_id), asdict(record))
        return record

    def due(self, now: datetime | None = None) -> list[BufferedDetection]:
        now = now or datetime.now(timezone.utc)
        items: list[BufferedDetection] = []
        for path in sorted(self.pending_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            record = BufferedDetection(**data)
            if record.status == "pending" and not record.next_attempt_at:
                items.append(record)
                continue
            if record.next_attempt_at is None:
                continue
            next_attempt = datetime.fromisoformat(record.next_attempt_at.replace("Z", "+00:00"))
            if next_attempt <= now:
                items.append(record)
        return items

    def mark_sent(self, event_id: str) -> None:
        pending = self._path("pending", event_id)
        if pending.exists():
            pending.unlink()
        self._atomic_write(self._path("sent", event_id), {"event_id": event_id, "status": "sent", "sent_at": datetime.now(timezone.utc).isoformat()})

    def mark_failed(self, event_id: str, payload: dict[str, Any], error: str, attempts: int) -> BufferedDetection:
        if attempts >= self.max_attempts:
            target = self._path("failed", event_id)
            record = BufferedDetection(event_id=event_id, payload=payload, attempts=attempts, status="failed", last_error=error)
            self._atomic_write(target, asdict(record))
            pending = self._path("pending", event_id)
            if pending.exists():
                pending.unlink()
            return record
        next_attempt = datetime.now(timezone.utc) + timedelta(seconds=self.backoff_seconds * max(1, attempts))
        record = BufferedDetection(event_id=event_id, payload=payload, attempts=attempts, status="pending", next_attempt_at=next_attempt.isoformat(), last_error=error)
        self._atomic_write(self._path("pending", event_id), asdict(record))
        return record

    def load(self, event_id: str) -> BufferedDetection | None:
        for state in ("pending", "failed", "sent"):
            path = self._path(state, event_id)
            if path.exists():
                return BufferedDetection(**json.loads(path.read_text(encoding="utf-8")))
        return None

    def pending_count(self) -> int:
        return len(list(self.pending_dir.glob("*.json")))
