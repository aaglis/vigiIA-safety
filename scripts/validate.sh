#!/usr/bin/env bash
set -euo pipefail

required_files=(
  "README.md"
  ".env.example"
  "package.json"
  "apps/web/README.md"
  "apps/web/package.json"
  "apps/web/index.html"
  "apps/web/vite.config.ts"
  "apps/web/tsconfig.json"
  "apps/web/tsconfig.node.json"
  "apps/web/tailwind.config.ts"
  "apps/web/postcss.config.js"
  "apps/web/src/main.tsx"
  "apps/web/src/App.tsx"
  "apps/web/src/index.css"
  "apps/web/Dockerfile"
  "apps/api/README.md"
  "apps/api/pyproject.toml"
  "apps/api/src/vigia_api/__init__.py"
  "apps/api/src/vigia_api/main.py"
  "apps/api/src/vigia_api/settings.py"
  "apps/api/src/vigia_api/api/v1/health.py"
  "apps/api/Dockerfile"
  "apps/edge-worker/README.md"
  "apps/edge-worker/Dockerfile"
  "packages/contracts/events/detection-event.v1.schema.json"
  "packages/contracts/events/edge-heartbeat.v1.schema.json"
  "packages/contracts/events/incident-created.v1.schema.json"
  "packages/contracts/events/notification-requested.v1.schema.json"
  "packages/contracts/events/notification-delivery-updated.v1.schema.json"
  "packages/contracts/permissions/permissions.yaml"
  "packages/contracts/openapi/README.md"
  "infra/compose/docker-compose.dev.yml"
  "infra/pdc/docker-compose.yml"
  "docs/architecture/repository-structure.md"
  "docs/architecture/overview.md"
  "docs/architecture/monorepo-structure.md"
  "docs/architecture/app-boundaries.md"
  "docs/architecture/saas-multitenancy.md"
  "docs/architecture/tenant-isolation.md"
  "docs/architecture/enterprise-deployment-path.md"
  "docs/architecture/identity-organization-schema.md"
  "docs/architecture/database-constraints.md"
  "docs/architecture/status-models.md"
  "docs/architecture/decisions.md"
  "docs/architecture/risks.md"
  "docs/architecture/flow.md"
  "docs/architecture/incident-notification-flow.md"
  "docs/architecture/notification-policy.md"
  "docs/architecture/domain-model.md"
  "docs/architecture/incident-lifecycle.md"
  "docs/architecture/roles-permissions.md"
  "docs/architecture/users-vs-workers.md"
  "docs/product/mvp-scope.md"
  "docs/product/pilot-plan.md"
  "docs/product/employee-portal-roadmap.md"
  "docs/product/out-of-scope-sprint-1.md"
  "docs/product/validation-metrics.md"
  "docs/customer/beta-handoff.md"
  "docs/customer/beta-readiness-checklist.md"
  "docs/customer/poc-assisted-proposal.md"
  "docs/security/lgpd-privacy-strategy.md"
  "docs/security/lgpd-audit-retention-policy.md"
  "docs/security/secret-management-policy.md"
  "docs/security/environment-separation.md"
  "docs/security/tenant-isolation-threat-model.md"
  "docs/security/evidence-retention.md"
  "docs/security/access-audit-policy.md"
  "docs/deployment/local-compose.md"
  "docs/deployment/pdc-compose.md"
  "docs/deployment/observability.md"
  "docs/deployment/secret-handling-checklist.md"
  "docs/deployment/ci.md"
  "docs/deployment/staging-pilot.md"
  "docs/deployment/staging-provisioning-plan.md"
  "docs/deployment/backup-restore.md"
  "docs/deployment/operational-jobs.md"
  "docs/edge-worker/overview.md"
  "packages/contracts/openapi/README.md"
  "docs/security/csrf-cors-rate-limit.md"
  "scripts/check-secrets.sh"
  "scripts/ci-smoke.sh"
  "scripts/pilot-smoke.sh"
  "scripts/staging-smoke.sh"
  "scripts/postgres-volume-smoke.sh"
)

for file in "${required_files[@]}"; do
  if [[ ! -s "$file" ]]; then
    echo "Arquivo obrigatório ausente ou vazio: $file" >&2
    exit 1
  fi
done

echo "Validação OK: documentação base presente."

if command -v python3 >/dev/null 2>&1; then
  python3 - <<'PY'
import json, pathlib
for path in [pathlib.Path('package.json'), pathlib.Path('apps/web/package.json')]:
    json.loads(path.read_text())
print('Validação OK: package.json files valid JSON.')
PY
else
  echo "Python3 indisponível; validação JSON ignorada."
fi

if command -v python3 >/dev/null 2>&1; then
  if [[ -f "apps/edge-worker/pyproject.toml" ]]; then
    PYTHONPATH="apps/edge-worker/src" python3 -m unittest discover -s apps/edge-worker/tests -p "test_*.py"
    echo "Validação OK: edge-worker tests executados."
  fi
  if [[ -d "apps/api/src" ]]; then
    python3 -m compileall apps/api/src >/dev/null
    echo "Validação OK: apps/api src compilado."
  fi
  if [[ -d "apps/api/tests" ]]; then
    PYTHONPATH="apps/api/src" python3 -m unittest discover -s apps/api/tests -p "test_*.py"
    echo "Validação OK: apps/api tests executados."
  fi
else
  echo "Python3 indisponível; testes do edge-worker ignorados."
fi
