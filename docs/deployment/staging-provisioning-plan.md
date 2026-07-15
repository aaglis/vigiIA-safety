# Plano de provisionamento de staging real

## Objetivo

Definir o caminho manual para criar o primeiro staging real do VigIA Safety sem registrar segredos no repositório, chat, cards ou logs compartilhados.

Este plano existe porque o ambiente desta sessão não possui repositório remoto detectado nem autenticação de deploy funcional. Portanto, ele **não prova que staging já existe**; ele descreve o que deve ser criado e como validar quando o provedor/repositório forem definidos.

## Decisão atual

- Provisionamento automático: **não executado**.
- Repositório remoto GitHub: **não detectado neste workspace**.
- Caminho escolhido para agora: **documentar e continuar localmente**.
- Próximo desbloqueio humano: escolher provedor, domínio, repositório/branch e configurar secrets fora do chat.

## Arquitetura mínima de staging

| Componente | Requisito |
| --- | --- |
| Web | HTTPS público, apontando para API staging |
| API | HTTPS público atrás de proxy/load balancer |
| PostgreSQL | Serviço real dedicado de staging; não usar `memory` |
| Redis | Serviço real para rate limit/cache; não usar `memory` |
| Storage S3/MinIO | Bucket privado dedicado; URL assinada gerada pela API |
| Edge worker | Serviço separado com credencial técnica própria |
| Observabilidade | Health/readiness públicos; metrics protegidas por `X-Metrics-Token` |

## Pré-requisitos humanos

Antes de provisionar:

1. Definir provedor de deploy.
2. Definir repositório remoto e branch de staging.
3. Definir domínios/subdomínios HTTPS, por exemplo:
   - `api-staging.<domínio>`
   - `app-staging.<domínio>`
4. Definir como serão criados PostgreSQL, Redis e bucket S3/MinIO.
5. Configurar secrets somente em painel/secret manager.
6. Confirmar responsável por rollback/pausa.

## Variáveis obrigatórias

Configurar no secret manager/painel, nunca em arquivo versionado:

- `APP_ENV=staging`
- `DATABASE_URL`
- `REPOSITORY_BACKEND=postgres`
- `REDIS_URL`
- `RATE_LIMIT_BACKEND=redis` ou `auto` com Redis real
- `JWT_SECRET`
- `REFRESH_TOKEN_SECRET`
- `COOKIE_SECURE=true`
- `ALLOWED_ORIGINS=https://app-staging.<domínio>`
- `METRICS_TOKEN`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `S3_ENDPOINT_URL=https://...`
- `ALLOW_INTERNAL_S3_ENDPOINT=true` only when the endpoint is internal `http://minio:9000` in a trusted compose/network
- `S3_REGION`
- `EVIDENCE_BUCKET_NAME`
- `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` se notificações SMTP forem usadas
- `EDGE_WORKER_CLIENT_ID`
- `EDGE_WORKER_API_KEY`
- `VITE_API_BASE_URL=https://api-staging.<domínio>`

Valores reais não devem aparecer em card, chat, commit, print ou relatório.

## Sequência de provisionamento

1. Criar PostgreSQL staging.
2. Criar Redis staging.
3. Criar bucket privado de evidências.
4. Criar serviço da API com `apps/api/Dockerfile`.
5. Criar serviço da Web com `apps/web/Dockerfile`.
6. Criar serviço/host do edge worker com `apps/edge-worker/Dockerfile`.
7. Configurar todos os secrets no painel.
8. Aplicar migrations da API.
9. Subir API e validar `/api/v1/health` e `/api/v1/readiness`.
10. Subir Web e validar HTTPS.
11. Subir edge worker em modo controlado.
12. Rodar `scripts/staging-smoke.sh` com variáveis `STAGING_*` vindas do ambiente seguro.

## Comandos de validação

Local, antes do deploy:

```bash
bash scripts/validate.sh
bash scripts/check-secrets.sh
```

Staging, depois do deploy, com variáveis fornecidas por secret manager/shell seguro:

```bash
STAGING_API_BASE_URL="https://api-staging.<domínio>" \
STAGING_WEB_BASE_URL="https://app-staging.<domínio>" \
STAGING_METRICS_TOKEN="<secret-manager>" \
bash scripts/staging-smoke.sh
```

Opcional para volume em Postgres isolado:

```bash
POSTGRES_VOLUME_SMOKE_DATABASE_URL="<database-url-isolada>" \
bash scripts/postgres-volume-smoke.sh
```

Não colar a saída se ela contiver segredos ou dados pessoais. Registre apenas status sanitizado: OK/falha, horário, versão, responsável e etapa que falhou.

## Critérios de pronto

Staging só pode ser marcado como pronto para POC quando:

- API e Web respondem por HTTPS;
- `scripts/staging-smoke.sh` passa;
- API usa `APP_ENV=staging`, Postgres e Redis reais;
- métricas exigem `X-Metrics-Token`;
- bucket de evidências é privado;
- edge worker publica heartbeat e envia detecção controlada;
- evidência é aberta somente sob demanda;
- auditoria registra triagem;
- logs compartilháveis não contêm secrets, cookies, headers sensíveis ou URL assinada.

## No-go

Não envolver cliente se:

- staging usa backend `memory`;
- há credenciais dev-only;
- bucket de evidências está público;
- API/Web não estão em HTTPS;
- metrics respondem sem token;
- qualquer secret aparece em log, chat, card ou print;
- incidente/evidência/auditoria aparece fora do tenant correto.

## Referências

- Runbook staging: [`staging-pilot.md`](./staging-pilot.md)
- Smoke staging: [`../../scripts/staging-smoke.sh`](../../scripts/staging-smoke.sh)
- Checklist readiness: [`../customer/beta-readiness-checklist.md`](../customer/beta-readiness-checklist.md)
- Proposta POC: [`../customer/poc-assisted-proposal.md`](../customer/poc-assisted-proposal.md)
- Segredos: [`../security/secret-management-policy.md`](../security/secret-management-policy.md)
