# Dev localhost — visão computacional

O stack sobe via Docker Compose. O worker de CV (YOLO) fica num **profile** separado
(`cv`) para não pesar quando você não precisa dele.

## Qual arquivo compose

`infra/compose/` tem dois:

- **`docker-compose.dev.yml`** — o stack completo (postgres, redis, minio, api, migrate,
  seed, web e o `edge-worker` de CV). **É este que você usa.**
- `docker-compose.local.yml` — só um Postgres avulso (gitignored), para rodar a API na mão.
  Não tem nada de CV.

Nenhum tem nome padrão, então `docker compose` não os pega sozinho. O `cp .env.example .env`
abaixo grava `COMPOSE_FILE=docker-compose.dev.yml` no `.env`, e aí o `docker compose up`
funciona limpo (sem `-f`).

## Comandos do dia a dia

Rode a partir de `infra/compose/` (para o `.env` ser lido):

```
cd infra/compose
cp .env.example .env                    # 1x (grava COMPOSE_FILE + defaults)

docker compose up --build               # base: postgres, redis, minio, api, web
docker compose --profile cv up --build  # base + worker de CV

docker compose logs -f edge-worker      # logs da detecção
docker compose down                     # derruba tudo
```

Sem o `.env`, passe o arquivo na mão: `docker compose -f docker-compose.dev.yml up`.

- Web: http://localhost:5173 · API: http://localhost:8000
- Login org-admin: `admin@vigia.local` / `change-me-dev`

## O que você precisa prover

1. **Vídeo** em `apps/edge-worker/assets/sample-ppe.mp4` (pessoa com/sem capacete + alguém
   entrando numa área restrita).
2. **Modelo de EPI** (opcional, para capacete): coloque um `.pt` com classe `helmet`/`head`
   em `apps/edge-worker/models/` e ajuste `CV_MODEL_PATH=/models/<arquivo>.pt` no `.env`.
   Sem isso, o `yolov8n.pt` (default) já valida **intrusão em zona restrita**.

## Fluxo

1. `docker compose up` sobe infra/API/web e roda o seed: cria a org, a câmera demo apontando
   para o vídeo, zonas ppe + restricted e o edge worker.
2. `docker compose --profile cv up` sobe o worker: ele lê `/edge-workers/me/config`, abre o
   stream da câmera (o vídeo), roda YOLO e envia detecções reais.
3. Cada violação vira incidente + evidência anotada no dashboard (`/incidents`, `/evidence`).

## One-shot vs contínuo

Por padrão o worker é **one-shot** (`EDGE_RUN_ONCE=true`): processa a fonte uma vez, emite os
incidentes e sai. É o modo bom para demo/teste — o container encerra e devolve a RAM.

Para o comportamento de produção (câmera 24/7), rode **contínuo** no `.env`:

```
EDGE_RUN_ONCE=false
EDGE_POLL_INTERVAL_SECONDS=30          # intervalo entre ciclos
EDGE_DETECTION_COOLDOWN_SECONDS=60     # não repete o mesmo incidente na janela
```

Comportamento por tipo de fonte:

- **Arquivo de vídeo** — o fim do arquivo encerra o ciclo; o loop reabre no próximo ciclo
  (reprocessa). Sem cooldown isso geraria incidentes repetidos a cada volta.
- **Stream ao vivo (RTSP/RTMP/HTTP)** — queda é tratada como transitória: o worker **reconecta
  sozinho** com backoff exponencial (`EDGE_RECONNECT_BACKOFF_SECONDS` → `EDGE_RECONNECT_MAX_BACKOFF_SECONDS`),
  logando `edge_worker.source_reconnect` / `edge_worker.source_unavailable`, sem derrubar o processo.

Medido no compose (vídeo, ciclos de 10s): worker vivo por 9 ciclos, memória estável
(~1.2 GiB, dentro do `mem_limit: 3g`), CPU limitada pelo `cpus: 3`, zero crash.

## RAM apertada

O worker carrega PyTorch (~2 GB). Em máquina com pouca RAM livre:

- `EDGE_RUN_ONCE=true` (default) faz o worker processar o vídeo e sair, liberando RAM.
- Suba a base primeiro e depois só o worker: `docker compose --profile cv up edge-worker`.
- Feche apps pesados (navegador) durante o build/execução.
