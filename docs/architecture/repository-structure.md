# Repository structure

## Visão geral
Monorepo do VigIA Safety com fronteiras explícitas entre aplicação web, API, worker de edge e contratos compartilhados.

Veja também: [monorepo structure](./monorepo-structure.md) e [app boundaries](./app-boundaries.md).

## Pastas principais
- `apps/web` — frontend React + Vite + TypeScript + Tailwind
- `apps/api` — backend FastAPI com persistência e autenticação
- `apps/edge-worker` — worker Python de visão computacional
- `packages/contracts` — schemas e permissões compartilhadas
- `infra/compose` — composição local de desenvolvimento
- `docs` — arquitetura e documentação do projeto
- `scripts` — automações e validações

## Regras de domínio
- Dados operacionais devem carregar `organization_id`
- API e edge worker são processos separados
- Workers operacionais não exigem login no MVP
