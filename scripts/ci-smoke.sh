#!/usr/bin/env bash
set -euo pipefail

compose_file="${COMPOSE_FILE:-infra/compose/docker-compose.dev.yml}"
project_name="${COMPOSE_PROJECT_NAME:-vigia_ci_smoke}"
export POSTGRES_HOST_PORT="${POSTGRES_HOST_PORT:-25432}"
export REDIS_HOST_PORT="${REDIS_HOST_PORT:-26379}"
export MINIO_HOST_PORT="${MINIO_HOST_PORT:-29000}"
export MINIO_CONSOLE_HOST_PORT="${MINIO_CONSOLE_HOST_PORT:-29001}"
export API_HOST_PORT="${API_HOST_PORT:-28000}"

cleanup() {
  docker compose -p "$project_name" -f "$compose_file" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "CI smoke: validando configuração do Compose..."
docker compose -p "$project_name" -f "$compose_file" config -q

echo "CI smoke: construindo imagens mínimas..."
docker compose -p "$project_name" -f "$compose_file" build api migrate seed edge-worker

echo "CI smoke: aplicando migrations em banco limpo..."
docker compose -p "$project_name" -f "$compose_file" run --rm migrate

echo "CI smoke: executando seed idempotente..."
docker compose -p "$project_name" -f "$compose_file" run --rm seed

echo "CI smoke: subindo API para teste HTTP..."
docker compose -p "$project_name" -f "$compose_file" up -d api


python3 - <<'PY'
from __future__ import annotations

import json
import time
import urllib.request

import os

url = f"http://127.0.0.1:{os.environ.get('API_HOST_PORT', '28000')}/api/v1/health"
last_error: Exception | None = None
for _ in range(40):
    try:
        with urllib.request.urlopen(url, timeout=3) as response:  # nosec B310 - CI local endpoint
            payload = json.loads(response.read().decode('utf-8'))
        if payload.get('status') in {'ok', 'degraded'}:
            print(f"CI smoke: health OK ({payload['status']}).")
            break
    except Exception as exc:  # pragma: no cover - shell smoke retry
        last_error = exc
    time.sleep(2)
else:
    raise SystemExit(f'API health não respondeu a tempo: {last_error}')
PY

echo "CI smoke: executando edge-worker HTTP uma vez..."
docker compose -p "$project_name" -f "$compose_file" run --rm edge-worker

echo "CI smoke: OK."
