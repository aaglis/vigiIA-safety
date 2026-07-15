#!/usr/bin/env bash
set -euo pipefail

database_url="${POSTGRES_VOLUME_SMOKE_DATABASE_URL:-${DATABASE_URL:-}}"
count="${POSTGRES_VOLUME_SMOKE_COUNT:-1000}"
days="${POSTGRES_VOLUME_SMOKE_DAYS:-30}"

if [[ -z "$database_url" ]]; then
  echo "POSTGRES_VOLUME_SMOKE_DATABASE_URL or DATABASE_URL is required" >&2
  exit 1
fi

if [[ "$database_url" != postgresql* ]]; then
  echo "database url must target PostgreSQL" >&2
  exit 1
fi

PYTHONPATH="apps/api/src" python3 -m vigia_api.scripts.seed_synthetic_incidents_postgres --database-url "$database_url" --count "$count" --days "$days"
