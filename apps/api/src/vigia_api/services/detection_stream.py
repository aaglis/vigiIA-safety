from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from threading import RLock
from typing import Any

# Fanout do que a CV está vendo AGORA. É estado efêmero de propósito: se ninguém está
# olhando a câmera, o frame morre aqui. O que precisa durar (incidente, evidência) segue
# pelo pipeline normal e vai para o Postgres.
MAX_QUEUE = 5


@dataclass(frozen=True)
class _Subscriber:
    queue: asyncio.Queue
    loop: asyncio.AbstractEventLoop


class DetectionHub:
    def __init__(self) -> None:
        self._subscribers: dict[tuple[str, str], dict[asyncio.Queue, _Subscriber]] = defaultdict(dict)
        self._lock = RLock()

    def subscribe(self, organization_id: str, camera_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE)
        subscriber = _Subscriber(queue=queue, loop=asyncio.get_running_loop())
        with self._lock:
            self._subscribers[(organization_id, camera_id)][queue] = subscriber
        return queue

    def unsubscribe(self, organization_id: str, camera_id: str, queue: asyncio.Queue) -> None:
        key = (organization_id, camera_id)
        with self._lock:
            if key not in self._subscribers:
                return
            self._subscribers[key].pop(queue, None)
            if not self._subscribers[key]:
                self._subscribers.pop(key, None)

    def subscriber_count(self, organization_id: str, camera_id: str) -> int:
        with self._lock:
            return len(self._subscribers.get((organization_id, camera_id), ()))

    @staticmethod
    def _put_latest(queue: asyncio.Queue, payload: dict[str, Any]) -> None:
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass

    def publish(self, organization_id: str, camera_id: str, payload: dict[str, Any]) -> int:
        """Não bloqueia nem espera: navegador lento perde o frame velho em vez de
        segurar a fila (melhor pular quadro do que atrasar o que está na tela).

        `frame-analysis` chega por endpoint síncrono (threadpool do FastAPI), enquanto o
        WebSocket roda no event loop. `asyncio.Queue` não é thread-safe, então a escrita é
        agendada no loop dono do assinante.
        """
        with self._lock:
            subscribers = tuple(self._subscribers.get((organization_id, camera_id), {}).values())
        for subscriber in subscribers:
            subscriber.loop.call_soon_threadsafe(self._put_latest, subscriber.queue, payload)
        return len(subscribers)
