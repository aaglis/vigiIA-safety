# VigIA Safety

VigIA Safety é uma plataforma SaaS multitenant para segurança industrial com visão computacional, focada em detecção de violações, evidências auditáveis e operação híbrida entre nuvem e edge.

## Comandos planejados
- `docker compose -f infra/compose/docker-compose.dev.yml up --build`
- `bash scripts/validate.sh`

## Stack inicial oficial
- Frontend: React + Vite + TypeScript + Tailwind
- API: FastAPI + Pydantic + SQLAlchemy/Alembic + PostgreSQL + Redis + MinIO/S3
- Edge/CV: Python + OpenCV + YOLO (futuro)

## Estrutura do repositório
- `apps/web` — frontend React + Vite + TypeScript + Tailwind
- `apps/api` — API FastAPI + SQLAlchemy/Alembic + PostgreSQL/Redis/MinIO
- `apps/edge-worker` — worker Python de visão computacional
- `packages/contracts` — schemas JSON e permissões
- `infra/compose` — skeleton de ambiente local
- `docs/architecture/repository-structure.md` — visão da organização do monorepo
- `docs/architecture/overview.md`
- `docs/architecture/monorepo-structure.md`
- `docs/architecture/app-boundaries.md`
- `docs/architecture/decisions.md`
- `docs/architecture/risks.md`
- `docs/architecture/flow.md`
- `docs/architecture/incident-notification-flow.md`
- `docs/architecture/notification-policy.md`
- `docs/architecture/domain-model.md`
- `docs/architecture/incident-lifecycle.md`
- `docs/architecture/roles-permissions.md`
- `docs/architecture/users-vs-workers.md`
- `docs/product/mvp-scope.md`
- `docs/product/employee-portal-roadmap.md`
- `docs/product/out-of-scope-sprint-1.md`
- `docs/product/validation-metrics.md`
- `docs/security/lgpd-privacy-strategy.md`
- `docs/security/evidence-retention.md`
- `docs/security/access-audit-policy.md`
- `docs/deployment/local-compose.md`
- `docs/edge-worker/overview.md`
- `docs/architecture/app-factory-repositories.md`
- `docs/architecture/operations-catalog-mvp.md`

## Diretriz principal
- API e worker de CV são apps separados.
- Todas as entidades operacionais pertencem a uma organização.
- Evidências ficam em storage privado com acesso auditado.

## Setup inicial
1. Copie `.env.example` para `.env`.
2. Suba a stack local com `docker compose -f infra/compose/docker-compose.dev.yml up --build`.
3. Frontend: `apps/web`.
4. Backend: `apps/api`.
5. Edge worker: `apps/edge-worker`.

> Dependências de Node/Python devem ser instaladas futuramente por ambiente.

## Links rápidos
- [Repository structure](docs/architecture/repository-structure.md)
- [Overview](docs/architecture/overview.md)
- [Monorepo structure](docs/architecture/monorepo-structure.md)
- [App boundaries](docs/architecture/app-boundaries.md)
- [SaaS multitenancy](docs/architecture/saas-multitenancy.md)
- [Tenant isolation](docs/architecture/tenant-isolation.md)
- [Enterprise deployment path](docs/architecture/enterprise-deployment-path.md)
- [Identity & organization schema](docs/architecture/identity-organization-schema.md)
- [Database constraints](docs/architecture/database-constraints.md)
- [Status models](docs/architecture/status-models.md)
- [Decisions](docs/architecture/decisions.md)
- [Risks](docs/architecture/risks.md)
- [Flow](docs/architecture/flow.md)
- [Incident notification flow](docs/architecture/incident-notification-flow.md)
- [Notification policy](docs/architecture/notification-policy.md)
- [Domain model](docs/architecture/domain-model.md)
- [Incident lifecycle](docs/architecture/incident-lifecycle.md)
- [Roles & permissions](docs/architecture/roles-permissions.md)
- [Users vs Workers](docs/architecture/users-vs-workers.md)
- [MVP scope](docs/product/mvp-scope.md)
- [Employee portal roadmap](docs/product/employee-portal-roadmap.md)
- [Out of scope — Sprint 1](docs/product/out-of-scope-sprint-1.md)
- [Validation metrics](docs/product/validation-metrics.md)
- [LGPD & privacy strategy](docs/security/lgpd-privacy-strategy.md)
- [Evidence retention](docs/security/evidence-retention.md)
- [Access & audit policy](docs/security/access-audit-policy.md)
- [Secret management policy](docs/security/secret-management-policy.md)
- [Environment separation](docs/security/environment-separation.md)
- [Secret handling checklist](docs/deployment/secret-handling-checklist.md)
- [Local compose deploy](docs/deployment/local-compose.md)
- [Edge worker overview](docs/edge-worker/overview.md)
- [Operations catalog MVP](docs/architecture/operations-catalog-mvp.md)
- [API pagination and filters](docs/api/pagination-and-filters.md)

> Produção exige segredos via ambiente/secret manager. Não copie valores reais para README, cards ou chat.
- [OpenAPI contracts](packages/contracts/openapi/README.md)
- [LGPD, audit & retention policy](docs/security/lgpd-audit-retention-policy.md)
- [RBAC policy](docs/security/rbac-policy.md)
- [Auth session strategy](docs/security/auth-session-strategy.md)
- [Platform admin](docs/architecture/platform-admin.md)
- [RBAC enforcement](docs/architecture/rbac-enforcement.md)
- [Organization invites](docs/architecture/org-invites.md)
- [Password reset & email verification](docs/security/password-reset-email-verification.md)

## Banco local
- `DATABASE_URL` vem do ambiente.
- Para dev local, use `infra/compose/docker-compose.local.yml` (arquivo ignorado pelo Git).
- Nunca exponha senha real em README, cards ou chat.

## Demo local com Docker Compose
- Suba com `docker compose -f infra/compose/docker-compose.dev.yml up --build`.
- O Compose roda `migrate` (`alembic upgrade head`) e `seed` antes da API iniciar.
- Migrations via Compose: `docker compose -f infra/compose/docker-compose.dev.yml run --rm migrate`.
- Seed persistente via Compose: `docker compose -f infra/compose/docker-compose.dev.yml run --rm seed`.
- Migrations via host: `cd apps/api && DATABASE_URL=postgresql+psycopg://vigia:vigia@localhost:15432/vigia alembic upgrade head`.
- Seed via host/Postgres: `cd apps/api && REPOSITORY_BACKEND=postgres DATABASE_URL=postgresql+psycopg://vigia:vigia@localhost:15432/vigia PYTHONPATH=src python -m vigia_api.scripts.seed_demo`.
- API: http://localhost:8000/api/v1/health
- Web: http://localhost:5173
- MinIO: http://localhost:9001
- `API_HOST_PORT`, `MINIO_HOST_PORT` e `MINIO_CONSOLE_HOST_PORT` permitem trocar portas publicadas no host.
- Postgres fica publicado no host em `localhost:15432` por padrão (`POSTGRES_HOST_PORT`).
- Redis fica publicado no host em `localhost:16379` por padrão (`REDIS_HOST_PORT`).
- A API no Compose usa `REPOSITORY_BACKEND=postgres`; testes locais usam `memory` por padrão.
- `docker compose down` preserva dados no volume PostgreSQL; `docker compose down -v` recria schema e seed no próximo `up --build`.
- O `edge-worker` chama a API real em modo HTTP e publica uma detecção mock como incidente usando credenciais dev-only.
- O seed cria a organização `org-demo`, alinhada aos IDs do edge-worker mock.

## CI e validação
- Gate rápido local: `bash scripts/validate.sh`.
- Varredura simples de segredos: `bash scripts/check-secrets.sh`.
- Smoke pesado de CI com Compose/migrations/HTTP: `bash scripts/ci-smoke.sh`.
- Detalhes: [CI e gates de qualidade](docs/deployment/ci.md).

Troubleshooting rápido:
- porta ocupada: pare o processo ou altere `POSTGRES_HOST_PORT`/`REDIS_HOST_PORT`/mapeamento do serviço;
- web sem API: verifique `VITE_API_BASE_URL`;
- health degradado: verifique Postgres/Redis/MinIO;
- edge-worker sem incidentes no dashboard: confira os logs do container e se a API registrou o worker demo `dev-client-id`/`dev-api-key` em `APP_ENV=dev`;
- auth falhando: confirme `APP_ENV=dev` e os segredos dev-only no compose.

Seed local sem compose:
- `cd apps/api && PYTHONPATH=src python -m vigia_api.scripts.seed_demo`
- Usuário demo: `admin@vigia.local`
- Senha dev-only: `change-me-dev`
- Organização demo: `org-demo` com membership `org_owner`
