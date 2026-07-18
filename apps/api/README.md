# apps/api

API principal do VigIA Safety.

## Stack
- FastAPI
- Pydantic
- PostgreSQL
- Redis
- MinIO/S3

## Responsabilidade
- autenticação e sessão;
- multi-tenant e RBAC;
- incidentes, auditoria e evidências;
- integração com edge workers por HTTP.

## Skeleton
- FastAPI em `src/vigia_api/main.py`
- Health router em `src/vigia_api/api/v1/health.py`
- Settings em `src/vigia_api/settings.py`
- Vertical slice de incidentes em `src/vigia_api/api/v1/incidents.py`
- Domínio puro/in-memory em `src/vigia_api/domain/incidents.py` e `src/vigia_api/services/incidents.py`
- Container compartilhado em `src/vigia_api/container.py` para incidentes e edge workers em memória

## Dev commands
- `python -m vigia_api.main`
- `PYTHONPATH=src python -m vigia_api.scripts.seed_demo`
- `python -m compileall src`
- `python -m unittest discover -s tests -p "test_*.py"`
- Migrations: `alembic -c alembic.ini upgrade head`
- Autogenerate: `alembic -c alembic.ini revision --autogenerate -m "message"`
- Postgres integration flows: `POSTGRES_TEST_DATABASE_URL=postgresql+psycopg://... bash ../../scripts/postgres-integration-tests.sh`
- Auth: `docs/security/auth-session-strategy.md`
- Platform admin: `docs/architecture/platform-admin.md`
- RBAC: `docs/architecture/rbac-enforcement.md`
- Org invites: `docs/architecture/org-invites.md`
- Password reset / verification: `docs/security/password-reset-email-verification.md`
- Security: `docs/security/csrf-cors-rate-limit.md`
- Evidence retention & purge: `docs/security/evidence-retention.md`
- Access audit policy: `docs/security/access-audit-policy.md`
- Observability MVP: `docs/deployment/observability.md`

## Notes
- API versionada em `/api/v1`.
- Todas as operações tenant-safe devem carregar `organization_id`.
- `DATABASE_URL` é configurado via ambiente; o healthcheck pode reportar status do banco sem expor credenciais.
- Persistência SQLAlchemy/Alembic está em fase inicial e pode coexistir com os repositórios in-memory.
- Evidências suportam `purge-preview` e `purge` com confirmação explícita.
- Logs estruturados e health/readiness expõem estado de dependências sem segredos.

## Demo local
- API: `uvicorn vigia_api.main:app --host 0.0.0.0 --port 8000`
- Health: `GET /api/v1/health`
- Se rodando via compose, use as credenciais dev-only do `.env.example`.
- Seed demo idempotente: `PYTHONPATH=src python -m vigia_api.scripts.seed_demo`
- Credenciais demo: `admin@vigia.local` / `change-me-dev`
- Organização demo: `org-demo` com membership `org_owner`.

## Teste contra Postgres real

Para validar os fluxos críticos no backend SQL real sem pesar o `validate` local:

```bash
export POSTGRES_TEST_DATABASE_URL="postgresql+psycopg://vigia:vigia@127.0.0.1:5432/vigia_test"
bash ../../scripts/postgres-integration-tests.sh
```

O script roda `alembic upgrade head` e depois apenas `test_postgres*.py`.

> Dependências ainda não estão instaladas neste repositório.
