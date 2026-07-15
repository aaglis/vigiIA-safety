# Observabilidade MVP

## Sinais mínimos
- request id/correlation id propagado via `X-Request-ID`;
- logs estruturados com `organization_id`, `incident_id` e `edge_worker_id` quando aplicável;
- health/readiness com estado de database, redis e minio;
- worker offline detectável por heartbeat atrasado;
- latência detection→incident registrada em ms;
- erros críticos sem segredos em payload/log.

## Métricas
- `requests_total` por rota/status;
- `request_latency_ms` por rota;
- `detections`, `incidents` e `worker_offline` como snapshots in-process.
- `edge_heartbeat` agrega heartbeats aceitos por organização/status.
- Em staging/prod, `/metrics` e `/api/v1/metrics` exigem `X-Metrics-Token`; em dev/local continuam livres para smoke.

## Operação
- use `health` para checar vivacidade e dependências;
- use `readiness` para o mesmo sinal sem expor segredos;
- use `metrics` para diagnóstico local;
- em staging/prod, exponha `X-Metrics-Token` apenas via tooling interno;
- use `python -m vigia_edge_worker.main --diagnose` para ver o estado local do worker sem conectar na API;
- monitore `edge_worker.heartbeat` e `edge_worker.detection_accepted`;
- acompanhe `incident.created` e `incident.transition`;
- revise logs de `evidence.upload_url`, `evidence.download` e `evidence.purge.*`.
