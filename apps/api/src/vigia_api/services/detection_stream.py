from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

# Fanout do que a CV está vendo AGORA. É estado efêmero de propósito: se ninguém está
# olhando a câmera, o frame morre aqui. O que precisa durar (incidente, evidência) segue
# pelo pipeline normal e vai para o Postgres.
MAX_QUEUE = 5


class DetectionHub:
    def __init__(self) -> None:
        self._subscribers: dict[tuple[str, str], set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, organization_id: str, camera_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE)
        self._subscribers[(organization_id, camera_id)].add(queue)
        return queue

    def unsubscribe(self, organization_id: str, camera_id: str, queue: asyncio.Queue) -> None:
        key = (organization_id, camera_id)
        self._subscribers[key].discard(queue)
        if not self._subscribers[key]:
            self._subscribers.pop(key, None)

    def subscriber_count(self, organization_id: str, camera_id: str) -> int:
        return len(self._subscribers.get((organization_id, camera_id), ()))

    def publish(self, organization_id: str, camera_id: str, payload: dict[str, Any]) -> int:
        """Não bloqueia nem espera: navegador lento perde o frame velho em vez de
        segurar a fila (melhor pular quadro do que atrasar o que está na tela)."""
        delivered = 0
        for queue in tuple(self._subscribers.get((organization_id, camera_id), ())):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(payload)
                delivered += 1
            except asyncio.QueueFull:
                continue
        return delivered
