# apps/edge-worker

Worker de visão computacional do VigIA Safety.

## Responsabilidade
- capturar streams locais;
- emitir eventos de detecção v1;
- enviar heartbeat;
- solicitar configuração e evidências autorizadas.

## Stack alvo
- Python
- OpenCV
- YOLO (futuro)

## Escopo inicial
- Processamento separado da API
- Captura e publicação de eventos de borda
- Healthcheck e heartbeat do nó edge
- Credencial técnica por worker/org

## Observação
O protótipo atual permanece em `src/vigia_edge_worker` e deve continuar compatível com o Dockerfile futuro.

## Execução protótipo
```bash
python -m vigia_edge_worker.main --mock --once
```

## Modo API real
```bash
EDGE_API_BASE_URL=http://localhost:8000/api/v1 \
EDGE_CLIENT_ID=dev-client-id \
EDGE_API_KEY=dev-api-key \
EDGE_RUN_ONCE=true \
python -m vigia_edge_worker.main --send-api
```

- `--mock --once` continua imprimindo/validando JSON local.
- Em modo API, o worker envia config/heartbeat/detection com headers `X-Edge-Client-Id` e `X-Edge-Api-Key`.

## Docker/demo local
- No compose, o worker pode usar `EDGE_API_BASE_URL`/`EDGE_API_KEY` para chamar a API real.
- Em `APP_ENV=dev`, a API registra automaticamente o worker demo `dev-client-id`/`dev-api-key` para smoke local.
- Se `EDGE_RUN_ONCE=true`, o container envia uma vez e sai.

## Contratos
- `packages/contracts/events/detection-event.v1.schema.json`
- `packages/contracts/events/edge-heartbeat.v1.schema.json`
