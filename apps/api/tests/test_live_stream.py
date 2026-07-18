from __future__ import annotations

import hashlib
import asyncio
import threading
import time
import unittest
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

from fastapi.testclient import TestClient

from vigia_api.api.v1 import streams
from vigia_api.main import create_app
from vigia_api.services.detection_stream import DetectionHub, MAX_QUEUE


@dataclass
class FakeSettings:
    jwt_secret: str = "test-secret"
    live_stream_public_base_url: str = "http://edge.local:8889"
    live_stream_ticket_ttl_seconds: int = 60
    frame_analysis_config_cache_seconds: float = 2.0


class FakeEdgeWorkerService:
    def __init__(self, config=None):
        self.calls = 0
        self._config = config or {"worker": {"id": "worker-1", "organization_id": "org-1"}, "cameras": [{"id": "cam-1"}]}

    def config(self, client_id, api_key):
        self.calls += 1
        if (client_id, api_key) != ("worker-1", "secret-1"):
            raise PermissionError("invalid credentials")
        return self._config


def build_client(edge_worker_service=None, hub=None, settings=None):
    container = SimpleNamespace(
        settings=settings or FakeSettings(),
        edge_worker_service=edge_worker_service or FakeEdgeWorkerService(),
        detection_hub=hub or DetectionHub(),
        operations_repository=None,
    )
    return TestClient(create_app(container=cast(Any, container))), container


class LiveStreamApiTest(unittest.TestCase):
    def setUp(self) -> None:
        streams._FRAME_ANALYSIS_CONFIG_CACHE.clear()

    def _start_subscriber(self, hub: DetectionHub, organization_id: str, camera_id: str):
        ready = threading.Event()
        stop = threading.Event()
        holder: dict[str, object] = {}

        def subscriber_thread():
            async def run():
                queue = hub.subscribe(organization_id, camera_id)
                holder["queue"] = queue
                ready.set()
                while not stop.is_set():
                    await asyncio.sleep(0.01)

            asyncio.run(run())

        thread = threading.Thread(target=subscriber_thread)
        thread.start()
        self.assertTrue(ready.wait(timeout=2))
        return holder, stop, thread

    def test_no_subscribers_returns_generic_accepted_and_skips_publish(self):
        client, container = build_client()
        called = False

        def fake_publish(*args, **kwargs):
            nonlocal called
            called = True

        container.detection_hub.publish = fake_publish  # type: ignore[method-assign]
        response = client.post(
            "/api/v1/edge-workers/me/frame-analysis",
            headers={"X-Edge-Client-Id": "worker-1", "X-Edge-Api-Key": "secret-1"},
            json={"camera_id": "cam-1", "timestamp": "2026-07-17T00:00:00Z", "boxes": [], "violations": []},
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"status": "accepted"})
        self.assertFalse(called)

    def test_active_subscriber_receives_latest_payload(self):
        client, container = build_client()

        async def listen_once():
            queue = container.detection_hub.subscribe("org-1", "cam-1")
            try:
                return await asyncio.wait_for(queue.get(), timeout=2)
            finally:
                container.detection_hub.unsubscribe("org-1", "cam-1", queue)

        result = {}

        def run_listener():
            result["payload"] = asyncio.run(listen_once())

        thread = threading.Thread(target=run_listener)
        thread.start()
        for _ in range(50):
            if container.detection_hub.subscriber_count("org-1", "cam-1"):
                break
            time.sleep(0.02)

        response = client.post(
            "/api/v1/edge-workers/me/frame-analysis",
            headers={"X-Edge-Client-Id": "worker-1", "X-Edge-Api-Key": "secret-1"},
            json={"camera_id": "cam-1", "timestamp": "2026-07-17T00:00:00Z", "boxes": [{"category": "person", "confidence": 0.9, "bbox": [1, 2, 3, 4]}], "violations": []},
        )
        thread.join(timeout=3)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"status": "accepted"})
        self.assertEqual(result["payload"]["camera_id"], "cam-1")
        self.assertEqual(result["payload"]["boxes"][0]["category"], "person")

    def test_invalid_credentials_and_unassigned_camera_are_forbidden_even_with_subscriber(self):
        client, container = build_client()
        holder, stop, thread = self._start_subscriber(container.detection_hub, "org-1", "cam-1")
        queue = cast(asyncio.Queue, holder["queue"])
        try:
            bad = client.post(
                "/api/v1/edge-workers/me/frame-analysis",
                headers={"X-Edge-Client-Id": "worker-1", "X-Edge-Api-Key": "wrong"},
                json={"camera_id": "cam-1", "timestamp": "2026-07-17T00:00:00Z", "boxes": [], "violations": []},
            )
            wrong_camera = client.post(
                "/api/v1/edge-workers/me/frame-analysis",
                headers={"X-Edge-Client-Id": "worker-1", "X-Edge-Api-Key": "secret-1"},
                json={"camera_id": "cam-2", "timestamp": "2026-07-17T00:00:00Z", "boxes": [], "violations": []},
            )
        finally:
            stop.set()
            container.detection_hub.unsubscribe("org-1", "cam-1", queue)
            thread.join(timeout=2)

        self.assertEqual(bad.status_code, 403)
        self.assertEqual(wrong_camera.status_code, 403)

    def test_response_does_not_leak_subscriber_counts(self):
        client, container = build_client()
        holder, stop, thread = self._start_subscriber(container.detection_hub, "org-1", "cam-1")
        queue = cast(asyncio.Queue, holder["queue"])
        try:
            response = client.post(
                "/api/v1/edge-workers/me/frame-analysis",
                headers={"X-Edge-Client-Id": "worker-1", "X-Edge-Api-Key": "secret-1"},
                json={"camera_id": "cam-1", "timestamp": "2026-07-17T00:00:00Z", "boxes": [], "violations": []},
            )
        finally:
            stop.set()
            container.detection_hub.unsubscribe("org-1", "cam-1", queue)
            thread.join(timeout=2)

        body = response.json()
        self.assertEqual(body, {"status": "accepted"})
        self.assertNotIn("delivered_to", body)
        self.assertNotIn("subscribers", body)
        self.assertNotIn("active", body)

    def test_auth_cache_reuses_config_within_ttl_and_refreshes_after(self):
        settings = FakeSettings(frame_analysis_config_cache_seconds=1.0)
        edge_worker_service = FakeEdgeWorkerService()
        client, _container = build_client(edge_worker_service=edge_worker_service, settings=settings)
        counter = {"n": 0}

        def fake_monotonic():
            counter["n"] += 1
            return 10.0 if counter["n"] < 3 else 12.0

        with patch.object(streams.time, "monotonic", side_effect=fake_monotonic):
            for _ in range(2):
                response = client.post(
                    "/api/v1/edge-workers/me/frame-analysis",
                    headers={"X-Edge-Client-Id": "worker-1", "X-Edge-Api-Key": "secret-1"},
                    json={"camera_id": "cam-1", "timestamp": "2026-07-17T00:00:00Z", "boxes": [], "violations": []},
                )
                self.assertEqual(response.status_code, 202)
            self.assertEqual(edge_worker_service.calls, 1)
            streams._FRAME_ANALYSIS_CONFIG_CACHE[("worker-1", hashlib.sha256(b"secret-1").hexdigest())] = (0.0, {"worker": {"id": "worker-1", "organization_id": "org-1"}, "cameras": [{"id": "cam-1"}]})
            response = client.post(
                "/api/v1/edge-workers/me/frame-analysis",
                headers={"X-Edge-Client-Id": "worker-1", "X-Edge-Api-Key": "secret-1"},
                json={"camera_id": "cam-1", "timestamp": "2026-07-17T00:00:00Z", "boxes": [], "violations": []},
            )
            self.assertEqual(response.status_code, 202)
        self.assertEqual(edge_worker_service.calls, 2)

    def test_publish_from_thread_keeps_latest_only_when_queue_overflows(self):
        hub = DetectionHub()
        ready = threading.Event()
        stop = threading.Event()
        holder: dict[str, object] = {}

        def subscriber_thread():
            async def run():
                queue = hub.subscribe("org-1", "cam-1")
                holder["queue"] = queue
                ready.set()
                while not stop.is_set():
                    await asyncio.sleep(0.01)

            asyncio.run(run())

        thread = threading.Thread(target=subscriber_thread)
        thread.start()
        self.assertTrue(ready.wait(timeout=2))
        queue = cast(asyncio.Queue, holder["queue"])
        try:
            for i in range(MAX_QUEUE + 2):
                hub.publish("org-1", "cam-1", {"frame": i})
            time.sleep(0.2)
            items = []
            while not queue.empty():
                items.append(queue.get_nowait())
            self.assertTrue(items)
            self.assertEqual(items[-1]["frame"], MAX_QUEUE + 1)
        finally:
            stop.set()
            hub.unsubscribe("org-1", "cam-1", queue)
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
