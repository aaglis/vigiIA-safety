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

eval_model="${CV_REAL_EVAL_MODEL_HOST_PATH:-apps/edge-worker/models/ppe-multiclass.pt}"
eval_recall_floor="${CV_REAL_EVAL_MIN_RECALL:-0.45}"
eval_report="/tmp/vigia-cv-real-eval.json"
if [[ -f "$eval_model" ]]; then
  echo "CI smoke: avaliando CV real em cv-real/v2 (recall mínimo EPI=${eval_recall_floor})..."
  eval_model_dir="$(cd "$(dirname "$eval_model")" && pwd)"
  eval_model_file="$(basename "$eval_model")"
  if ! docker compose -p "$project_name" -f "$compose_file" --profile cv run --rm --no-deps \
    -v "$PWD/apps/edge-worker/datasets:/datasets:ro" \
    -v "$eval_model_dir:/eval-model:ro" \
    -e YOLO_CONFIG_DIR=/tmp/Ultralytics \
    --entrypoint python edge-worker -m vigia_edge_worker.evaluation_real \
    --dataset /datasets/cv-real/v2/manifest.json \
    --model "/eval-model/${eval_model_file}" \
    --conf 0.4 \
    --min-samples 30 \
    --min-helmet-samples 1 \
    --min-empty-samples 1 \
    --min-ppe-recall "$eval_recall_floor" > "$eval_report"; then
    python3 - <<'PY'
from pathlib import Path

report = Path('/tmp/vigia-cv-real-eval.json')
print(report.read_text(encoding='utf-8')[-1000:] if report.exists() else 'sem relatório de avaliação CV')
PY
    exit 1
  fi
  python3 - <<'PY'
from __future__ import annotations

import json
from pathlib import Path

text = Path('/tmp/vigia-cv-real-eval.json').read_text(encoding='utf-8')
payload = json.loads(text[text.find('{'):])
ppe = payload['ppe_violation']
coverage = payload['coverage_summary']
print(
    'CI smoke: CV real OK '
    f"samples={coverage['total_samples']} helmet={coverage['helmet_samples']} "
    f"empty={coverage['empty_samples']} recall={ppe['recall']} precision={ppe['precision']}"
)
PY
elif [[ "${CV_REAL_EVAL_REQUIRED:-0}" == "1" ]]; then
  echo "CI smoke: modelo CV real obrigatório não encontrado em ${eval_model}."
  exit 1
else
  echo "CI smoke: avaliação CV real ignorada (modelo não encontrado em ${eval_model})."
fi

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
