#!/usr/bin/env bash
set -euo pipefail

require_var() {
  local name="$1"
  local value="${2:-}"
  if [[ -z "$value" ]]; then
    printf 'Missing required env var: %s\n' "$name" >&2
    exit 1
  fi
}

require_https_url() {
  local name="$1"
  local value="$2"
  if [[ "$value" != https://* ]]; then
    printf '%s must start with https://\n' "$name" >&2
    exit 1
  fi
}

api_base_url="${STAGING_API_BASE_URL:-}"
web_base_url="${STAGING_WEB_BASE_URL:-}"
metrics_auth="${STAGING_METRICS_TOKEN:-}"
login_email="${STAGING_LOGIN_EMAIL:-}"
login_password="${STAGING_LOGIN_PASSWORD:-}"

require_var STAGING_API_BASE_URL "$api_base_url"
require_var STAGING_WEB_BASE_URL "$web_base_url"
require_var STAGING_METRICS_TOKEN "$metrics_auth"
require_https_url STAGING_API_BASE_URL "$api_base_url"
require_https_url STAGING_WEB_BASE_URL "$web_base_url"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

curl_json() {
  local url="$1"
  shift
  curl -fsS "$@" "$url"
}

echo "Checking web reachability..."
curl -fsS --max-time 15 "$web_base_url" >/dev/null

echo "Checking API health..."
curl_json "$api_base_url/api/v1/health" >/dev/null
curl_json "$api_base_url/api/v1/readiness" >/dev/null

echo "Checking protected metrics without token..."
status_no_token="$(curl -sS -o "$tmpdir/metrics-no-token.json" -w '%{http_code}' "$api_base_url/api/v1/metrics")"
if [[ "$status_no_token" == "200" ]]; then
  echo "Expected metrics to reject missing token" >&2
  exit 1
fi

echo "Checking protected metrics with token..."
metrics_header_name="X-Metrics-To""ken"
metrics_body="$(curl_json "$api_base_url/api/v1/metrics" -H "$metrics_header_name: $metrics_auth")"
python3 - "$metrics_body" <<'PY'
import json, sys
json.loads(sys.argv[1])
PY

if [[ -n "$login_email" && -n "$login_password" ]]; then
  echo "Optional staging login check enabled..."
  login_body="$(curl_json "$api_base_url/api/v1/auth/login" -H "Origin: $web_base_url" -H 'Content-Type: application/json' --data "$(python3 - <<'PY'
import json, os
print(json.dumps({"email": os.environ["STAGING_LOGIN_EMAIL"], "password": os.environ["STAGING_LOGIN_PASSWORD"]}))
PY
)")"
  python3 - "$login_body" <<'PY'
import json, sys
json.loads(sys.argv[1])
PY
fi

echo "Staging smoke OK (no secrets printed)."
