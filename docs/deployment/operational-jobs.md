# Jobs operacionais

## Execução
- One-shot manual: `python -m vigia_api.scripts.jobs_runner ...`
- Scheduler automático: `python -m vigia_api.scripts.jobs_scheduler`

## Flags úteis
- `--threshold-seconds` para considerar worker offline.
- `--confirm` para executar purge de evidências.
- `--now` em ISO-8601 para execução determinística em testes.
- `--once` para executar um ciclo do scheduler e sair.
- `--organization-id` para limitar o ciclo a um tenant.

## Notas
- Os jobs são idempotentes e tenant-safe.
- O scheduler usa lock Redis por job (`SET NX EX`) e falha seguro se o Redis não estiver disponível.
- Notificações saem da fila quando o scheduler roda; o incidente continua persistido antes do envio.
- Notificações controladas cobrem somente severidade alta/crítica; em dev/test o envio é mock/in-memory, e em staging/prod o Resend precisa de `RESEND_API_KEY`, `NOTIFICATION_FROM` e `INCIDENT_NOTIFICATION_RECIPIENTS` fortes quando `INCIDENT_NOTIFICATION_MODE=resend`.
- WhatsApp não faz parte deste card.
- Evidence retention continua como dry-run por padrão; o scheduler só faz purge quando `scheduler_evidence_retention_confirm=true`.
