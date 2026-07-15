#!/usr/bin/env bash
set -euo pipefail

compose_file="${COMPOSE_FILE:-infra/compose/docker-compose.dev.yml}"
project_name="${COMPOSE_PROJECT_NAME:-vigia_pilot_smoke}"
export POSTGRES_HOST_PORT="${POSTGRES_HOST_PORT:-35432}"
export REDIS_HOST_PORT="${REDIS_HOST_PORT:-36379}"
export MINIO_HOST_PORT="${MINIO_HOST_PORT:-39000}"
export MINIO_CONSOLE_HOST_PORT="${MINIO_CONSOLE_HOST_PORT:-39001}"
export API_HOST_PORT="${API_HOST_PORT:-38000}"
export WEB_HOST_PORT="${WEB_HOST_PORT:-35173}"

cleanup() {
  docker compose -p "$project_name" -f "$compose_file" down --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Pilot smoke: validando Compose isolado..."
docker compose -p "$project_name" -f "$compose_file" config -q

echo "Pilot smoke: construindo imagens necessárias..."
docker compose -p "$project_name" -f "$compose_file" build api migrate seed web edge-worker >/dev/null

echo "Pilot smoke: subindo infraestrutura e app local..."
docker compose -p "$project_name" -f "$compose_file" up -d postgres redis minio api web >/dev/null

python3 - <<'PY'
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

API = f"http://127.0.0.1:{os.environ.get('API_HOST_PORT', '38000')}/api/v1"
WEB = f"http://127.0.0.1:{os.environ.get('WEB_HOST_PORT', '35173')}"
HEADERS = {"Origin": "http://localhost:3000", "Referer": "http://localhost:3000/"}


def request_json(url: str, method: str = "GET", data: dict | None = None, headers: dict | None = None, opener=None):
    payload = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=payload, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    with (opener.open(req, timeout=5) if opener else urllib.request.urlopen(req, timeout=5)) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body) if body else {}


def wait_json(url: str, attempts: int = 45):
    last = None
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2)
    raise SystemExit(f"Timeout aguardando {url}: {last}")


status, health = wait_json(f"{API}/health")
if status != 200 or health.get("status") not in {"ok", "degraded"}:
    raise SystemExit(f"API health inválido: {health}")
print(f"Pilot smoke: health OK ({health.get('status')}).")

status, readiness = wait_json(f"{API}/readiness")
if status != 200 or readiness.get("status") not in {"ok", "degraded"}:
    raise SystemExit(f"API readiness inválido: {readiness}")

status, metrics = wait_json(f"{API}/metrics")
if status != 200 or "requests_total" not in metrics:
    raise SystemExit("API metrics sem requests_total")

jar = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
status, login = request_json(f"{API}/auth/login", method="POST", data={"email": "admin@vigia.local", "password": "change-me-dev"}, headers=HEADERS, opener=opener)
if status != 200 or login.get("me", {}).get("active_organization", {}).get("id") != "org-demo":
    raise SystemExit(f"Login demo falhou: status={status}")

csrf_value = next((cookie.value for cookie in jar if cookie.name == "csrf_token" or cookie.name.endswith("csrf")), None)
if not csrf_value:
    raise SystemExit("CSRF cookie não encontrado após login")

status, me = request_json(f"{API}/auth/me", opener=opener)
if status != 200 or me.get("user", {}).get("email") != "admin@vigia.local":
    raise SystemExit("/auth/me inválido")

status, incident_list = request_json(f"{API}/organizations/org-demo/incidents", opener=opener)
if status != 200:
    raise SystemExit("Listagem de incidentes falhou")
if not incident_list.get("items"):
    raise SystemExit("Seed local não expôs incidentes para o dashboard")

incident_id = incident_list["items"][0]["id"]
status, incident = request_json(f"{API}/organizations/org-demo/incidents/{incident_id}", opener=opener)
if status != 200:
    raise SystemExit("Detalhe do incidente falhou")

status = urllib.request.urlopen(f"{WEB}/", timeout=5).status
if status != 200:
    raise SystemExit(f"Web HTTP inválido: {status}")

print(json.dumps({"incident_id": incident_id, "web": True}, ensure_ascii=False))
PY

echo "Pilot smoke: validando worker em modo API e emitindo uma detecção..."
docker compose -p "$project_name" -f "$compose_file" run --rm edge-worker python -m vigia_edge_worker.main --once --send-api >/dev/null

python3 - <<'PY'
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

API = f"http://127.0.0.1:{os.environ.get('API_HOST_PORT', '38000')}/api/v1"
HEADERS = {"Origin": "http://localhost:3000", "Referer": "http://localhost:3000/"}


def request_json(url: str, method: str = "GET", data: dict | None = None, headers: dict | None = None, opener=None):
    payload = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(url, data=payload, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    with (opener.open(req, timeout=5) if opener else urllib.request.urlopen(req, timeout=5)) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body) if body else {}


jar = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
status, login = request_json(f"{API}/auth/login", method="POST", data={"email": "admin@vigia.local", "password": "change-me-dev"}, headers=HEADERS, opener=opener)
if status != 200 or login.get("me", {}).get("active_organization", {}).get("id") != "org-demo":
    raise SystemExit("Login demo falhou após executar edge-worker")

for _ in range(30):
    status, payload = request_json(f"{API}/organizations/org-demo/incidents", opener=opener)
    evidence_count = 0
    selected = None
    for item in payload.get("items", []):
        status, evidence = request_json(f"{API}/organizations/org-demo/evidence?incident_id={item['id']}", opener=opener)
        evidence_count = len(evidence.get("items", []))
        if evidence_count > 0:
            selected = item
            break
    if selected is not None:
        incident = selected
        break
    time.sleep(2)
else:
    raise SystemExit("Nenhum incidente com evidência encontrado após executar o edge-worker")

if not all(incident.get(key) for key in ("id", "status", "created_at")):
    raise SystemExit(f"Incidente incompleto no dashboard/API: {incident}")

print(f"Pilot smoke: incidente com evidência disponível no dashboard ({incident['id']}, evidências={evidence_count}).")
PY

echo "Pilot smoke: OK."
