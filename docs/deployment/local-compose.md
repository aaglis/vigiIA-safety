# Deploy local com Docker Compose

## Objetivo
Descrever o ambiente local do monorepo sem acoplar os apps em runtime.

Para piloto/staging, use `docs/deployment/staging-pilot.md`; o Compose local usa credenciais dev-only e não deve ser promovido como configuração de staging.

## Componentes
- `apps/web` — container do frontend.
- `apps/api` — container da API.
- `apps/edge-worker` — container opcional para simulação local da borda.
- `infra/compose/docker-compose.dev.yml` — orquestração do ambiente.

## Regras
- Cada app deve continuar com Dockerfile próprio.
- O Compose apenas sobe serviços; não define fronteira de código.
- Cada app pode ser implantado separadamente em produção.

## Variáveis importantes
- `DATABASE_URL`
- `REPOSITORY_BACKEND` — `memory` para testes locais isolados; `postgres` para Compose/demo persistente.
- `POSTGRES_HOST_PORT` — porta publicada no host para Postgres; padrão `15432` para evitar conflito com bancos locais.
- `REDIS_HOST_PORT` — porta publicada no host para Redis; padrão `16379` para evitar conflito com Redis local.
- `API_HOST_PORT` — porta publicada no host para API; padrão `8000`.
- `MINIO_HOST_PORT` e `MINIO_CONSOLE_HOST_PORT` — portas publicadas para MinIO; padrões `9000` e `9001`.
- `MINIO_ENDPOINT`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `EVIDENCE_BUCKET_NAME`
- `EVIDENCE_PRESIGNED_URL_TTL_SECONDS`

## Fluxo recomendado
- Subir demo persistente completa: `docker compose -f infra/compose/docker-compose.dev.yml up --build`.
- Aplicar migrations via Compose: `docker compose -f infra/compose/docker-compose.dev.yml run --rm migrate`.
- Executar seed persistente via Compose: `docker compose -f infra/compose/docker-compose.dev.yml run --rm seed`.
- Reproduzir smoke pesado de CI: `bash scripts/ci-smoke.sh`.
- Reproduzir smoke de piloto local com Web, edge e evidência: `bash scripts/pilot-smoke.sh`.
- Reproduzir E2E browser do dashboard com API mockada: `npm --workspace apps/web run test:e2e`.
- Aplicar migrations via host: `cd apps/api && DATABASE_URL=postgresql+psycopg://vigia:vigia@localhost:15432/vigia alembic upgrade head`.
- Executar seed via host: `cd apps/api && REPOSITORY_BACKEND=postgres DATABASE_URL=postgresql+psycopg://vigia:vigia@localhost:15432/vigia PYTHONPATH=src python -m vigia_api.scripts.seed_demo`.

## Observações
- O bucket de evidências deve ser privado.
- URLs assinadas são geradas pela API.
- O compose local serve para desenvolvimento e validação do fluxo.
- O smoke de piloto local usa `COMPOSE_PROJECT_NAME=vigia_pilot_smoke` por padrão, não derruba volumes compartilhados e não exige segredos reais.
- O compose local usa `REPOSITORY_BACKEND=postgres` e roda `alembic upgrade head` no serviço `migrate` antes da API.
- Ao subir a stack, o serviço `migrate` aplica o schema e o serviço `seed` prepara `org-demo` antes da API iniciar.
- A web deve apontar para `http://localhost:8000/api/v1`.
- O `edge-worker` pode chamar a API real usando `EDGE_API_BASE_URL`, `EDGE_CLIENT_ID`, `EDGE_API_KEY` e `EDGE_RUN_ONCE=true`.
- O smoke de piloto valida `/health`, `/readiness`, `/metrics`, login demo, incidente, evidência e a resposta HTTP da Web; o teste visual manual do dashboard continua opcional.
- O E2E browser usa Playwright, cobre login, lista/detalhe de incidente, evidência sob demanda e ação de triagem; em máquina nova rode `npx playwright install chromium` antes.
- A API responde em `http://localhost:8000/api/v1/health`.
- O MinIO console fica em `http://localhost:9001`.
- Internamente os containers continuam usando Postgres `postgres:5432` e Redis `redis:6379`; as portas `15432`/`16379` são apenas para acesso pelo host.

## Troubleshooting
- API não sobe: confira `DATABASE_URL`, `REDIS_URL` e `MINIO_ENDPOINT`.
- Seed falha por schema ausente: rode `docker compose -f infra/compose/docker-compose.dev.yml run --rm migrate` e depois `docker compose -f infra/compose/docker-compose.dev.yml run --rm seed`.
- Web sem dados: confirme `VITE_API_BASE_URL` no compose/Dockerfile.
- Worker não publica incidente: confira se a API subiu saudável e se `EDGE_CLIENT_ID`/`EDGE_API_KEY` batem com `EDGE_WORKER_CLIENT_ID`/`EDGE_WORKER_API_KEY` da API.
- Smoke sem evidência após o worker: confira logs do `edge-worker`, registro de `evidence` na API e conectividade com MinIO/storage; o seed sozinho não garante evidência binária.
- Health degradado: verifique dependências locais e credenciais dev-only.
- Porta ocupada no host: ajuste `POSTGRES_HOST_PORT` ou `REDIS_HOST_PORT` antes de subir a stack.

## Observabilidade mínima
- health/readiness expõe status de database/redis/minio;
- logs estruturados carregam `organization_id`, `incident_id` e `edge_worker_id` quando aplicável;
- o worker pode ser considerado offline por heartbeat atrasado;
- o caminho `detection -> incident` registra latência em ms.

## Seed demo
- Host/local: `cd apps/api && PYTHONPATH=src python -m vigia_api.scripts.seed_demo`
- Host/local com PostgreSQL: `cd apps/api && REPOSITORY_BACKEND=postgres DATABASE_URL=postgresql+psycopg://vigia:vigia@localhost:15432/vigia PYTHONPATH=src python -m vigia_api.scripts.seed_demo`
- Compose: `docker compose -f infra/compose/docker-compose.dev.yml run --rm seed`
- Usuário demo: `admin@vigia.local`
- Senha dev-only: `change-me-dev`
- Organização demo: `org-demo`, alinhada ao worker mock e aos IDs `site-demo`, `camera-demo-01` e `zone-demo-01`.
- `docker compose down` preserva o volume PostgreSQL e o seed segue idempotente.
- `docker compose down -v` remove o volume; no próximo `up --build`, migrations e seed recriam schema/dados sem duplicidade.

## Estado atual do edge-worker
- O container `edge-worker` chama a API real em modo HTTP e publica uma detecção mock como incidente quando `EDGE_RUN_ONCE=true`.
- Em `APP_ENV=dev`, a API registra automaticamente o worker demo `dev-client-id`/`dev-api-key` para smoke local.
- Se não aparecer incidente no dashboard, verifique `docker compose -f infra/compose/docker-compose.dev.yml logs edge-worker`.
