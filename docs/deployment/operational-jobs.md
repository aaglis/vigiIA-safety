# Jobs operacionais

## Comandos
- `python -m vigia_api.scripts.jobs_runner offline-workers --organization-id org-1`
- `python -m vigia_api.scripts.jobs_runner evidence-retention --organization-id org-1 --confirm --reason cleanup`
- `python -m vigia_api.scripts.jobs_runner notifications --organization-id org-1`
- `python -m vigia_api.scripts.jobs_runner all --organization-id org-1`

## Flags úteis
- `--threshold-seconds` para considerar worker offline.
- `--confirm` para executar purge de evidências.
- `--now` em ISO-8601 para execução determinística em testes.

## Notas
- Os jobs são idempotentes e tenant-safe.
- Notificações usam fila in-memory existente; não há tabela nova neste card.
- Notificações controladas cobrem somente severidade alta/crítica; em dev/test o envio é mock/in-memory, e em staging/prod o SMTP precisa de configuração forte ou o envio é suprimido/falha sem bloquear o incidente.
- WhatsApp não faz parte deste card.
- Em produção, este runner pode ser invocado por cron, worker de fila ou scheduler externo.
