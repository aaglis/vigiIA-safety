#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${POSTGRES_TEST_DATABASE_URL:-}" ]]; then
  echo "POSTGRES_TEST_DATABASE_URL is required" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
api_dir="$repo_root/apps/api"

sanitize_url() {
  python3 - <<'PY'
import os
from urllib.parse import urlsplit, urlunsplit

raw = os.environ["POSTGRES_TEST_DATABASE_URL"]
parts = urlsplit(raw)
netloc = parts.hostname or ""
if parts.port:
    netloc += f":{parts.port}"
print(urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment)))
PY
}

echo "Postgres integration: using $(sanitize_url)"

cd "$api_dir"

for attempt in $(seq 1 30); do
  if DATABASE_URL="$POSTGRES_TEST_DATABASE_URL" python3 - <<'PY'
from sqlalchemy import create_engine, text
import os
import sys

try:
    engine = create_engine(os.environ["DATABASE_URL"], future=True)
    with engine.connect() as connection:
        connection.execute(text("select 1"))
    engine.dispose()
except Exception:
    sys.exit(1)
PY
  then
    break
  fi
  if [[ "$attempt" == "30" ]]; then
    echo "Postgres integration: database did not become ready" >&2
    exit 1
  fi
  sleep 1
done

DATABASE_URL="$POSTGRES_TEST_DATABASE_URL" POSTGRES_TEST_DATABASE_URL="$POSTGRES_TEST_DATABASE_URL" python3 -m alembic upgrade head
PYTHONPATH=src DATABASE_URL="$POSTGRES_TEST_DATABASE_URL" POSTGRES_TEST_DATABASE_URL="$POSTGRES_TEST_DATABASE_URL" python3 -m unittest discover -s tests -p "test_postgres*.py"
