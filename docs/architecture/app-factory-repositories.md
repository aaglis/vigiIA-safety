# App factory e repositórios

## App factory
- A API é montada por `vigia_api.main.create_app()`.
- `app = create_app()` permanece para Uvicorn.
- Cada app recebe um `AppContainer` explícito em `app.state.container`.
- Testes podem criar containers próprios com `build_container(repository_backend="memory")` sem compartilhar estado com a app global.

## Backend de repositórios
- `REPOSITORY_BACKEND=memory`: padrão de testes rápidos e desenvolvimento isolado.
- `REPOSITORY_BACKEND=postgres`: usa SQLAlchemy/PostgreSQL para edge workers, incidentes/auditoria e metadados/auditoria de evidências.
- `staging` e `production` recusam `memory` no bootstrap de settings.

## Limite atual
- Auth, recovery, invites e platform admin ainda usam repositório in-memory centralizado por app.
- O refactor atual remove múltiplas instâncias divergentes por app, mas a persistência completa de auth fica para um passo posterior.

## Migrations e Compose
- Migrations não rodam no startup da API.
- O Compose dev usa `REPOSITORY_BACKEND=postgres` e um serviço `migrate` executando `alembic upgrade head` antes da API.
- Para testes unitários no host, mantenha `REPOSITORY_BACKEND=memory`.
