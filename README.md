# VigIA Safety

Plataforma SaaS multitenant que usa visão computacional para flagrar violações de segurança do trabalho — pessoa sem capacete, invasão de área restrita — a partir das câmeras que a planta **já tem**, gerando incidente com evidência auditável.

A câmera não é nosso produto: é equipamento do cliente. Nós consumimos o RTSP dela.

## Como funciona

```
câmera IP (RTSP)
   └─> edge worker: YOLO detecta pessoas e capacetes
        └─> regra: os pés da pessoa estão dentro do polígono da zona?
             └─> API: vira incidente (com dedup)
                  └─> dashboard: incidente + frame anotado como evidência
```

Duas coisas que explicam quase todo o resto do sistema:

**O polígono é uma região 2D da imagem, e a regra é "os pés estão dentro dela".** Como a imagem não tem profundidade, um polígono só significa "a pessoa está aqui" se for desenhado **no chão**. Marcado numa parede ou porta, ele dispara com quem passa *na frente*, não com quem entra.

**O modelo define quais regras existem.** Se o modelo não sabe ver capacete, a regra de EPI não roda — em vez de acusar todo mundo, o worker reporta a regra como inativa. Não se afirma a ausência do que não se consegue enxergar.

## Rodando local

Precisa de: Docker + Docker Compose. (Node 20+ e Python 3.11+ só se for rodar web/API fora do container.)

### 1. Baixe o que não vem no Git

Modelo e vídeos **não são versionados** (pesados demais). Sem eles a CV não sobe:

```bash
# Modelo YOLO (pessoa + capacete). Detalhes e checagem de segurança em apps/edge-worker/models/README.md
curl -L -o apps/edge-worker/models/ppe-multiclass.pt \
  https://huggingface.co/Hansung-Cho/yolov8-ppe-detection/resolve/main/best.pt
```

Para os vídeos que fazem o papel das câmeras, jogue qualquer `.mp4` em `apps/edge-worker/assets/`. O seed espera `sample-ppe.mp4`, `pexels-262484.mp4` e `pixabay-13439512.mp4` — veja `apps/edge-worker/assets/README.md` para onde baixar (Pexels/Pixabay, uso livre).

> **`.pt` é um pickle do Python: carregar executa código.** Não baixe modelo de origem desconhecida sem seguir o procedimento de inspeção em `apps/edge-worker/models/README.md`.

### 2. Suba

```bash
cd infra/compose
cp .env.example .env

docker compose --profile cv up --build          # sistema + worker de CV
docker compose -f docker-compose.cameras.yml up -d   # as câmeras
```

A ordem importa: o primeiro compose cria a rede `vigia-dev`, o segundo entra nela — é assim que o worker alcança a câmera por hostname, como faria na LAN da planta.

Migrations e seed rodam sozinhos antes da API subir.

### 3. Entre

| | |
|---|---|
| Web | http://localhost:5173 |
| API | http://localhost:8000/api/v1/health |
| MinIO (evidências) | http://localhost:9001 |
| Login demo | `admin@vigia.local` / `change-me-dev` (org `org-demo`, papel `org_owner`) |

Sem o `--profile cv` você tem o SaaS inteiro, só sem visão computacional — é o suficiente para mexer em front, auth ou incidentes.

## Configuração

Nenhum segredo é necessário para dev: **tudo tem default no compose**, e o `.env` só serve para ajustar. Copiar o `.env.example` é opcional (ele existe para documentar as opções e deixar o `docker compose` achar o arquivo certo sem `-f`).

Os que mais importam:

| Variável | Default | Para quê |
|---|---|---|
| `CV_MODEL_PATH` | `/models/ppe-multiclass.pt` | Trocar o modelo. COCO (`yolov8n.pt`) não vê capacete e desativa a regra de EPI |
| `EDGE_RUN_ONCE` | `false` | Worker fica vivo, como câmera 24/7. `true` = analisa a fonte uma vez e para |
| `EDGE_VIDEO_FRAME_STRIDE` | `15` | Processa 1 a cada N frames; maior = mais leve |
| `CV_CONFIDENCE_THRESHOLD` | `0.4` | Confiança mínima da detecção |
| `POSTGRES_HOST_PORT` | `15432` | Trocar se a porta estiver ocupada |

Lista completa em `infra/compose/.env.example`.

**Produção exige segredos reais via ambiente ou secret manager.** Nunca cole valor real em README, card ou chat — veja [política de segredos](docs/security/secret-management-policy.md).

## Estrutura

| Pasta | O que é |
|---|---|
| `apps/web` | Front React + Vite + TypeScript + Tailwind |
| `apps/api` | API FastAPI + SQLAlchemy/Alembic (Postgres, Redis, MinIO) |
| `apps/edge-worker` | Worker Python de CV (OpenCV + YOLO/ultralytics) |
| `packages/contracts` | Schemas JSON e permissões compartilhados |
| `infra/compose` | Ambiente local (sistema + câmeras) |

Regras que valem em todo o repo: API e worker são apps separados; toda entidade operacional pertence a uma organização; evidência fica em storage privado com acesso auditado.

## Testes

```bash
bash scripts/validate.sh          # gate rápido (roda antes de commitar)
bash scripts/check-secrets.sh     # varredura de segredos

# API (179 testes)
cd apps/api && PYTHONPATH=src uv run python -m unittest discover -s tests -t tests -p "test_*.py"

# Edge worker (51 testes) — rodar da RAIZ do repo
PYTHONPATH="apps/edge-worker/src" python3 -m unittest discover -s apps/edge-worker/tests -p "test_*.py"

# Web, ponta a ponta
npm --workspace apps/web run test:e2e
```

Os testes da API usam repositório em memória por default (`REPOSITORY_BACKEND=memory`); o compose usa Postgres.

## Documentação

Comece por aqui:

| | |
|---|---|
| [Visão geral da arquitetura](docs/architecture/overview.md) | Como as peças se encaixam |
| [CV em localhost](docs/development/cv-localhost.md) | Subir a visão computacional na sua máquina |
| [Câmeras em dev](docs/development/cameras-dev.md) | Como um `.mp4` vira câmera RTSP |
| [Modelos de CV](apps/edge-worker/models/README.md) | Qual modelo usar e **como verificar se é seguro** |
| [Acurácia da CV](docs/product/acuracia-cv.md) | O que medimos, e o que o número **não** diz |
| [Escopo do MVP](docs/product/mvp-scope.md) | O que está dentro e fora |

<details>
<summary>Arquitetura</summary>

- [Estrutura do monorepo](docs/architecture/monorepo-structure.md) · [Fronteiras entre apps](docs/architecture/app-boundaries.md) · [Estrutura do repositório](docs/architecture/repository-structure.md)
- [Modelo de domínio](docs/architecture/domain-model.md) · [Fluxo](docs/architecture/flow.md) · [Ciclo de vida do incidente](docs/architecture/incident-lifecycle.md)
- [Multitenancy](docs/architecture/saas-multitenancy.md) · [Isolamento de tenant](docs/architecture/tenant-isolation.md) · [Identidade e organizações](docs/architecture/identity-organization-schema.md)
- [Papéis e permissões](docs/architecture/roles-permissions.md) · [Enforcement de RBAC](docs/architecture/rbac-enforcement.md) · [Platform admin](docs/architecture/platform-admin.md)
- [Usuários vs workers](docs/architecture/users-vs-workers.md) · [Vídeo ao vivo](docs/architecture/live-video.md) · [Catálogo de operações](docs/architecture/operations-catalog-mvp.md)
- [Notificação de incidente](docs/architecture/incident-notification-flow.md) · [Política de notificação](docs/architecture/notification-policy.md) · [Convites](docs/architecture/org-invites.md)
- [Decisões](docs/architecture/decisions.md) · [Riscos](docs/architecture/risks.md) · [Restrições de banco](docs/architecture/database-constraints.md) · [Modelos de status](docs/architecture/status-models.md)
- [App factory e repositórios](docs/architecture/app-factory-repositories.md) · [Caminho de deploy enterprise](docs/architecture/enterprise-deployment-path.md)

</details>

<details>
<summary>Segurança e privacidade</summary>

- [LGPD e privacidade](docs/security/lgpd-privacy-strategy.md) · [LGPD, auditoria e retenção](docs/security/lgpd-audit-retention-policy.md) · [Retenção de evidências](docs/security/evidence-retention.md)
- [Política de RBAC](docs/security/rbac-policy.md) · [Sessão e auth](docs/security/auth-session-strategy.md) · [Reset de senha e verificação de e-mail](docs/security/password-reset-email-verification.md)
- [Auditoria de acesso](docs/security/access-audit-policy.md) · [Gestão de segredos](docs/security/secret-management-policy.md) · [Separação de ambientes](docs/security/environment-separation.md)

</details>

<details>
<summary>Produto e operação</summary>

- [Roadmap do portal do funcionário](docs/product/employee-portal-roadmap.md) · [Métricas de validação](docs/product/validation-metrics.md) · [Posicionamento vs PixForce](docs/product/positioning-vs-pixforce.md)
- [Deploy local](docs/deployment/local-compose.md) · [CI e gates](docs/deployment/ci.md) · [Backup e restore](docs/deployment/backup-restore.md) · [Baseline de volume](docs/deployment/incident-volume-baseline.md)
- [Paginação e filtros da API](docs/api/pagination-and-filters.md) · [Contratos OpenAPI](packages/contracts/openapi/README.md) · [Worker de edge](docs/edge-worker/overview.md)

</details>

## Quando algo não sobe

| Sintoma | Quase sempre é |
|---|---|
| Worker não gera incidente de EPI | Modelo sem classe de capacete — confira `CV_MODEL_PATH` e o `inactive_rules` no heartbeat |
| Worker não sobe | Faltou baixar o `.pt` em `apps/edge-worker/models/` |
| Câmera não abre | O compose de câmeras não está de pé, ou o `.mp4` não está em `assets/` |
| Porta ocupada | Ajuste `POSTGRES_HOST_PORT` / `REDIS_HOST_PORT` / `API_HOST_PORT` |
| Web sem API | `VITE_API_BASE_URL` |
| Health degradado | Postgres, Redis ou MinIO fora |
| Login falhando | Confirme `APP_ENV=dev` |

`docker compose down` preserva o banco. `docker compose down -v` apaga o volume e recria schema + seed no próximo `up`.
