# Staging reproduzível para piloto controlado

## Objetivo
Definir um ambiente de staging seguro, reproduzível e próximo de produção para validar o VigIA Safety fora da máquina local antes de qualquer piloto com usuários externos.

Este runbook não executa deploy automaticamente e não deve conter segredos reais. Valores sensíveis devem ser configurados apenas no secret manager ou painel da plataforma de deploy.

Para o checklist manual de criação do primeiro ambiente, veja [`staging-provisioning-plan.md`](./staging-provisioning-plan.md).

## Topologia mínima
- **API**: container `apps/api`, exposto por HTTPS atrás de proxy/load balancer.
- **Web**: container `apps/web`, servido por HTTPS e apontando para a API staging.
- **PostgreSQL**: banco gerenciado ou instância dedicada de staging.
- **Redis**: cache/rate limit compartilhado dedicado de staging.
- **Storage S3 compatível**: bucket privado para evidências, com URLs assinadas geradas pela API.
- **Edge worker**: container/serviço separado usando credencial técnica própria de staging.
- **Domínio/HTTPS**: subdomínios dedicados, por exemplo `api-staging.<domínio>` e `app-staging.<domínio>`.

## Regras de isolamento
- Staging nunca usa credenciais, buckets, filas, API keys ou banco de produção.
- Staging nunca usa credenciais `dev-only`, `change-me`, `example`, `vigia`, `test` ou placeholders.
- Staging não usa `REPOSITORY_BACKEND=memory` nem `RATE_LIMIT_BACKEND=memory`.
- Segredos reais não entram no repositório, cards, logs colados no chat ou screenshots.
- Dados reais de pessoas só entram em staging com aprovação explícita e base legal/operacional definida.

## Variáveis obrigatórias
Configure no painel/secret manager do ambiente, não em arquivo versionado:

| Variável | Regra para staging |
| --- | --- |
| `APP_ENV` | `staging` |
| `DATABASE_URL` | URL do PostgreSQL staging; não pode ser placeholder |
| `REPOSITORY_BACKEND` | `postgres` |
| `REDIS_URL` | URL do Redis staging; não pode apontar para dev/prod por engano |
| `RATE_LIMIT_BACKEND` | `redis` ou `auto` com Redis disponível |
| `JWT_SECRET` | segredo forte e exclusivo de staging |
| `REFRESH_TOKEN_SECRET` | segredo forte e exclusivo de staging |
| `COOKIE_SECURE` | `true`; cookies de auth não podem trafegar fora de HTTPS |
| `ALLOWED_ORIGINS` | lista explícita de origens HTTPS da Web staging, sem localhost/http |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | credenciais fortes do storage staging |
| `S3_ENDPOINT_URL` / `S3_REGION` | endpoint HTTPS/região do storage staging; API precisa ter dependência `boto3` instalada |
| `EVIDENCE_BUCKET_NAME` | bucket privado dedicado de staging |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | credenciais de envio staging, não dev-only |
| `SMTP_FROM` | remetente permitido para staging |
| `EDGE_WORKER_CLIENT_ID` / `EDGE_WORKER_API_KEY` | credencial técnica forte e exclusiva do worker staging |
| `VITE_API_BASE_URL` | URL pública HTTPS da API staging para o frontend |

## Valores proibidos
- `REPOSITORY_BACKEND=memory`.
- `RATE_LIMIT_BACKEND=memory`.
- `APP_ENV=dev` ou `APP_ENV=production` no ambiente de staging.
- `COOKIE_SECURE=false`, origem `http://`, `localhost` ou `127.0.0.1` em `ALLOWED_ORIGINS`.
- Qualquer valor contendo `dev-only`, `change-me`, `example`, `placeholder`, `todo`, `replace-me`, `smtp.dev.local`, `dev-client-id` ou `dev-api-key`.
- `DATABASE_URL`, `REDIS_URL`, storage ou SMTP apontando para local/dev/prod por reaproveitamento.
- `S3_ENDPOINT_URL` ausente, não-HTTPS ou dependência `boto3` ausente na imagem da API.
- Bucket de evidências público ou política de storage permitindo leitura anônima.

## Checklist de evidências assinadas
- Bucket de evidências privado validado antes do smoke.
- URLs assinadas aparecem somente após ação explícita no dashboard.
- Logs de API, Web e edge worker não contêm query string de URL assinada, `X-Amz-Signature`, tokens, cookies ou headers `X-Edge-*`.
- TTL de URL assinada revisado para o piloto e menor que a janela de triagem operacional.
- Edge worker usa headers `X-Edge-*` apenas contra a API; upload para storage usa somente a URL assinada.

## Ordem de deploy
1. Criar serviços externos: PostgreSQL, Redis e bucket privado de evidências.
2. Configurar secrets no painel/secret manager.
3. Buildar e publicar imagens de API, Web e Edge Worker a partir da mesma revisão de código.
4. Rodar migrations da API: `alembic upgrade head` no container da API com env staging.
5. Opcional para demo controlada: rodar seed staging idempotente somente se aprovado pelo responsável do piloto.
6. Subir API e validar `/api/v1/health`, `/api/v1/readiness` e `/api/v1/metrics`.
   - `X-Metrics-Token` é obrigatório em staging; usar tooling interno para o smoke.
7. Subir Web apontando para `VITE_API_BASE_URL` da API staging.
8. Subir Edge Worker com `EDGE_API_BASE_URL`, `EDGE_CLIENT_ID`, `EDGE_API_KEY`, `CV_MODE` e source configurados para o piloto.

## Smoke pós-deploy
Execute após cada deploy de staging:

Preferir o script `scripts/staging-smoke.sh` com variáveis de ambiente seguras; ele valida HTTPS, health/readiness, métricas protegidas e reachability do Web sem imprimir segredos.

### API
```bash
curl -fsS https://api-staging.example.invalid/api/v1/health
curl -fsS https://api-staging.example.invalid/api/v1/readiness
curl -fsS -H "X-Metrics-Token: <token-do-secret-manager>" https://api-staging.example.invalid/api/v1/metrics
```

Critérios:
- health/readiness sem dependência degradada;
- metrics responde sem segredos;
- logs da API têm `request_id` e não expõem secrets.

### Web
1. Abrir a URL HTTPS da Web staging.
2. Fazer login com usuário de staging autorizado.
3. Confirmar que o dashboard carrega a organização correta.
4. Confirmar que modo demo local não foi ativado por falha de API.

### Edge worker
Diagnóstico local do container/host do worker:
```bash
python -m vigia_edge_worker.main --diagnose
```

Smoke controlado de detecção:
```bash
EDGE_RUN_ONCE=true python -m vigia_edge_worker.main --once --send-api
```

Critérios:
- heartbeat aceito pela API;
- detecção cria ou reaproveita incidente idempotente pelo mesmo `event_id`;
- fila offline (`pending_queue`) volta para `0` quando a API está disponível;
- logs estruturados do worker incluem câmera/site/organização e não incluem `EDGE_API_KEY`.

### Evidência e dashboard
1. Abrir o incidente gerado no dashboard.
2. Confirmar `confidence`, `model_version`, câmera, zona, site e timestamp.
3. Se houver evidência, clicar em “Abrir evidência segura”.
4. Confirmar que a URL assinada só aparece após o clique e expira conforme política.
5. Confirmar estados vazios quando não houver snapshot/clip.

## Rollback básico
- Manter a imagem anterior da API/Web/Worker identificada por tag imutável.
- Se o deploy quebrar API ou Web, voltar a task/release para a imagem anterior e reexecutar health/readiness.
- Se migrations novas já foram aplicadas, só fazer rollback de banco com plano explícito; preferir migration forward de correção.
- Se o worker gerar ruído, parar apenas o serviço do worker, preservar API/Web e analisar buffer offline antes de apagar qualquer arquivo.
- Nunca apagar bucket de evidências como tentativa de rollback.
- Para recuperação de dados, seguir `docs/deployment/backup-restore.md` antes de qualquer ação destrutiva.

## Leitura de logs
- API: procurar `edge_worker.detection_accepted`, `edge_worker.detection_rejected`, `edge_worker.heartbeat`, `incident.transition` e eventos de evidência.
- Worker: procurar `edge_worker.detection_emitted`, `edge_worker.detection_send_failed`, `edge_worker.heartbeat_sent`, `edge_worker.heartbeat_failed`.
- Observabilidade: usar `/api/v1/metrics` para `requests_total`, `request_latency_ms`, `detections`, `incidents`, `worker_offline` e `edge_heartbeat`.

## Diferença entre smoke local e staging
- `bash scripts/validate.sh`: gate rápido local/CI; não prova deploy.
- `bash scripts/check-secrets.sh`: varredura de repositório; não valida secret manager.
- `bash scripts/ci-smoke.sh`: smoke local com Docker Compose e credenciais dev-only isoladas.
- `bash scripts/pilot-smoke.sh`: smoke local de piloto com Web/evidência/dashboard em Compose isolado; ainda não substitui staging real.
- Smoke staging: roda contra URLs HTTPS e serviços reais de staging, com secrets externos e backends não-memory.

## Ferramenta de deploy
Se uma ferramenta gerenciada de deploy estiver disponível, use este runbook para confirmar nome do projeto, repositório, branch, porta, variáveis e serviços antes de criar ou alterar o ambiente. Não dispare deploy, restart, stop ou troca de branch de produção sem confirmação humana explícita.
