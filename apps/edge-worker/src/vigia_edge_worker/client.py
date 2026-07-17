from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _mask(value: str | None) -> str:
    if not value:
        return ""
    return value[:4] + "***"


@dataclass
class EdgeApiClient:
    base_url: str
    client_id: str
    api_key: str
    timeout: int = 10
    opener: Callable = urlopen
    request_id: str | None = None

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
        request = Request(self.base_url.rstrip("/") + path, data=body, method=method)
        request.add_header("Content-Type", "application/json")
        request.add_header("X-Edge-Client-Id", self.client_id)
        request.add_header("X-Edge-Api-Key", self.api_key)
        request.add_header("X-Request-ID", self.request_id or uuid4().hex)
        try:
            with self.opener(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            raise RuntimeError(f"edge api request failed ({method} {path}): HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"edge api request failed ({method} {path}): network error") from exc

    def get_config(self) -> dict:
        return self._request("GET", "/edge-workers/me/config")

    def send_heartbeat(self, payload: dict) -> dict:
        return self._request("POST", "/edge-workers/me/heartbeat", payload)

    def send_detection(self, payload: dict) -> dict:
        return self._request("POST", "/edge-workers/me/detections", payload)

    def publish_frame_analysis(self, payload: dict) -> dict:
        """O que a CV vê no frame atual (só coordenadas). Best-effort: alimenta o overlay
        ao vivo e não pode atrapalhar o pipeline de incidentes se falhar."""
        return self._request("POST", "/edge-workers/me/frame-analysis", payload)

    def send_detection_with_retry(self, payload: dict, attempts: int = 1) -> dict:
        last_error: Exception | None = None
        for _ in range(max(1, attempts)):
            try:
                return self.send_detection(payload)
            except RuntimeError as exc:
                last_error = exc
        assert last_error is not None
        raise last_error

    def request_evidence_upload(self, file_id: str, incident_id: str | None = None) -> dict:
        path = f"/edge-workers/me/evidence-upload?file_id={file_id}"
        if incident_id:
            path += f"&incident_id={incident_id}"
        return self._request("POST", path)

    def upload_evidence_bytes(self, upload_ref: dict, data: bytes, content_type: str = "application/octet-stream") -> dict[str, object]:
        upload_url = upload_ref.get("upload_url") or upload_ref.get("url")
        if not upload_url:
            return {"status": "skipped", "reason": "no_upload_url"}
        request = Request(str(upload_url), data=data, method="PUT")
        request.add_header("Content-Type", content_type)
        request.add_header("Content-Length", str(len(data)))
        try:
            with self.opener(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return {"status": "uploaded", "response": json.loads(raw) if raw else {}}
        except HTTPError as exc:
            raise RuntimeError(f"evidence upload failed: HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError("evidence upload failed: network error") from exc

    def describe(self) -> str:
        return f"{self.base_url} client_id={_mask(self.client_id)} api_key={_mask(self.api_key)}"
