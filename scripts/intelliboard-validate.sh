#!/usr/bin/env bash
set -euo pipefail

# Fast validation gate for Intelliboard MCP card completion.
# The full local/CI gate remains `bash scripts/validate.sh`; this smoke stays
# below the MCP timeout while still catching broken docs, secrets and web build.

bash scripts/check-secrets.sh

python -m json.tool package.json >/dev/null
python -m json.tool apps/web/package.json >/dev/null

test -f docs/deployment/pdc-compose.md
test -f docs/deployment/staging-pilot.md
test -f infra/pdc/docker-compose.yml
test -f apps/web/nginx.conf

npm --workspace apps/web run build

echo "Validação OK: Intelliboard smoke passou."
