# CI e gates de qualidade

## Gates obrigatórios
- `bash scripts/validate.sh` — documentação base, JSON, compile da API e testes `unittest` de API/edge-worker.
- `bash scripts/check-secrets.sh` — varredura simples para segredos reais fora da allowlist de exemplos/dev-only.
- `bash scripts/ci-smoke.sh` — valida Compose, build mínimo, `alembic upgrade head`, seed e smoke HTTP da API/edge-worker.
- `bash scripts/pilot-smoke.sh` — smoke local mais completo: API, Web, seed, incidente, evidência e dashboard, em projeto Compose isolado.
- `npm --workspace apps/web run test:e2e` — E2E browser do dashboard com Playwright e API mockada, cobrindo login, incidente, evidência sob demanda e ação de triagem.
- `PYTHONPATH=apps/api/src python3 -m vigia_api.scripts.seed_synthetic_incidents --count 1000` — baseline local de volume sintético para filtros do dashboard.
- `bash scripts/backup-restore-smoke.sh` — smoke isolado de backup/restore local para PostgreSQL e MinIO quando a máquina tiver Docker disponível.

## Reproduzir localmente
```bash
bash scripts/validate.sh
bash scripts/check-secrets.sh
bash scripts/ci-smoke.sh
bash scripts/pilot-smoke.sh
npm --workspace apps/web run test:e2e
PYTHONPATH=apps/api/src python3 -m vigia_api.scripts.seed_synthetic_incidents --count 1000
```

O smoke usa `COMPOSE_PROJECT_NAME=vigia_ci_smoke` por padrão, publica portas isoladas (`API_HOST_PORT=28000`, `POSTGRES_HOST_PORT=25432`, `REDIS_HOST_PORT=26379`, `MINIO_HOST_PORT=29000`) e remove os volumes desse projeto ao finalizar.

Para a primeira execução do E2E browser em uma máquina nova, instale o navegador de teste com `npx playwright install chromium`. O teste usa mocks e não exige segredos reais nem stack Docker.

## Checks pesados vs rápidos
- Rápidos: `validate.sh` e `check-secrets.sh`.
- Médio: `npm --workspace apps/web run test:e2e`, por subir Vite e executar Chromium headless.
- Médio: runner de volume sintético, por criar 1k+ incidentes fake e medir filtros em memória.
- Pesado obrigatório em CI: `ci-smoke.sh`, por construir imagens e subir Postgres/Redis/MinIO.
- Pesado local/operacional: `pilot-smoke.sh`, por validar fluxo de piloto sem segredos reais e sem destruir volumes compartilhados.
- Pesado operacional sob demanda: `backup-restore-smoke.sh`, por destruir volumes do projeto Compose isolado e validar restore básico.
- Staging: siga `docs/deployment/staging-pilot.md`; o smoke local não substitui validação em domínio HTTPS, secrets externos e backends não-memory.

## Allowlist de placeholders
Valores dev-only continuam permitidos em `.env.example`, Compose dev e docs de segurança/deploy. Segredos reais não devem aparecer em arquivos versionados.

## Smoke local vs staging
- Local/CI usa `scripts/ci-smoke.sh` com projeto Compose isolado e credenciais dev-only permitidas.
- Local piloto usa `scripts/pilot-smoke.sh` com Compose isolado e verificação de Web + evidência.
- E2E browser usa Playwright com API mockada para provar a experiência do usuário sem expor URL assinada antes do clique.
- Staging deve validar `/health`, `/readiness`, `/metrics`, login real, edge worker em API mode, incidente no dashboard e evidência sob demanda.
- Staging deve bloquear `REPOSITORY_BACKEND=memory`, `RATE_LIMIT_BACKEND=memory` e placeholders de secrets.
