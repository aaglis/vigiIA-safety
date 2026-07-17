# Backup, restore e runbooks operacionais

## Objetivo
Definir procedimentos mínimos para proteger dados do VigIA Safety durante beta privado e produção inicial, cobrindo PostgreSQL, evidências em storage S3/MinIO, rotação de segredos e resposta a incidentes operacionais.

Nenhum comando abaixo deve incluir segredos reais em logs compartilhados, cards ou chat.

## Escopo de dados
- PostgreSQL: usuários, sessões, memberships, catálogo operacional, incidentes, auditoria e metadados de evidência.
- S3/MinIO: snapshots, clipes e objetos privados de evidência.
- Redis: cache/rate limit/fila transitória; não é fonte de verdade para restore funcional.
- Edge worker: buffer offline local pode conter detecções pendentes e precisa ser preservado antes de apagar máquina/disco.

## RPO/RTO iniciais
| Ambiente | RPO inicial | RTO inicial | Observação |
| --- | --- | --- | --- |
| Beta privado | até 24h | até 8h | aceito para piloto assistido, com comunicação ao cliente |
| Produção inicial | até 4h | até 2h | exige automação e teste periódico de restore |

RPO/RTO devem ser revisados antes de qualquer SLA comercial.

## Política de backup
### PostgreSQL
- Backup lógico diário (`pg_dump`) no beta privado.
- Backup gerenciado/PITR quando o provedor oferecer, obrigatório antes de produção inicial.
- Retenção mínima: 7 dias em beta, 30 dias em produção inicial.
- Backup deve ser criptografado em repouso pelo provedor ou storage de destino.

### S3/MinIO
- Bucket de evidências privado.
- Versionamento habilitado quando disponível.
- Backup/snapshot diário do bucket ou replicação para storage isolado.
- Retenção alinhada à política LGPD/auditoria de evidências.

### Redis
- Não restaurar Redis como fonte de verdade.
- Em perda de Redis, recriar serviço e aceitar reset de rate limit/cache.
- Se houver fila futura persistente, criar política própria antes de produção.

## Smoke local de restore
Use o script isolado para provar que o fluxo básico PostgreSQL + MinIO é restaurável com dados demo:

```bash
bash scripts/backup-restore-smoke.sh
```

O script:
1. sobe Compose em projeto isolado;
2. aplica migrations e seed demo;
3. gera `pg_dump` e snapshot do volume MinIO;
4. destrói volumes do projeto isolado;
5. restaura PostgreSQL e MinIO;
6. valida `admin@vigia.local` e `org-demo` no banco restaurado.

Não rode este script contra ambiente real. Ele usa `docker compose down -v` no projeto configurado.

### Baseline sintético de Postgres
Depois do restore isolado, ou contra qualquer Postgres de staging/dev isolado, rode o baseline de volume:

```bash
POSTGRES_VOLUME_SMOKE_DATABASE_URL='postgresql+psycopg://user:pass@localhost:5432/vigia' bash scripts/postgres-volume-smoke.sh
```

O resultado esperado é JSON com medidas de listagem, filtros, detalhe, auditoria e evidência para 1k+ incidentes sintéticos, sem segredos nem URLs assinadas.

### Execução isolada registrada

Última execução sanitizada em ambiente local isolado:

- `bash scripts/backup-restore-smoke.sh`: OK; dump PostgreSQL e snapshot MinIO gerados em diretório temporário, volumes recriados e dados demo (`admin@vigia.local`, `org-demo`) restaurados com sucesso.
- `bash scripts/postgres-volume-smoke.sh` com Postgres isolado e 1k incidentes sintéticos: OK; nenhum segredo, URL assinada ou dado real foi registrado.

Resultado de volume PostgreSQL com 1k incidentes sintéticos:

| Caminho medido | Itens | Tempo |
| --- | ---: | ---: |
| Primeira página | 50 | 25.372ms |
| Filtro status aberto | 50 | 10.412ms |
| Filtro severidade alta | 50 | 7.805ms |
| Filtro site/câmera/zona | 50 | 4.435ms |
| Filtro últimos 7 dias | 50 | 10.776ms |
| Detalhe | 1 | 1.800ms |
| Auditoria | 1 | 2.564ms |
| Evidência metadata-only | 1 | 1.578ms |

Recomendação atual: manter índices para `organization_id + created_at`, `organization_id + status + severity` e o combo site/câmera/zona mais usado pelo cliente, reavaliando com dados sintéticos maiores antes de produção.

## Restore local manual
### PostgreSQL
```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d postgres
docker compose -f infra/compose/docker-compose.dev.yml exec -T postgres psql -U vigia -d vigia < backup/postgres.sql
```

### MinIO local
```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d minio
docker compose -f infra/compose/docker-compose.dev.yml exec -T minio sh -c 'tar -xzf - -C /data' < backup/minio-data.tgz
```

### Verificação pós-restore
```bash
docker compose -f infra/compose/docker-compose.dev.yml run --rm migrate
docker compose -f infra/compose/docker-compose.dev.yml up -d api
curl -fsS http://localhost:8000/api/v1/health
curl -fsS http://localhost:8000/api/v1/readiness
```

## Restore staging/produção
1. Abrir incidente operacional interno e registrar janela de restore.
2. Congelar deploys e workers de escrita quando possível.
3. Restaurar banco por mecanismo do provedor ou dump validado.
4. Restaurar/reativar bucket de evidências.
5. Rodar migrations pendentes apenas se a versão de app exigir.
6. Subir API e validar health/readiness/metrics.
7. Subir Web e validar login/dashboard.
8. Subir edge workers gradualmente.
9. Conferir auditoria, evidência e incidente demo/controlado.
10. Registrar resultado, horário e responsável.

## Rotação de segredos
- Seguir `docs/security/secret-management-policy.md`.
- Rotação planejada: trocar secret no secret manager, reiniciar serviços afetados e validar login/edge worker.
- Rotação emergencial: revogar segredo antigo, invalidar sessões/tokens quando aplicável e revisar logs de uso indevido.
- Edge worker: revogar credencial por `client_id`/`worker_id`, emitir nova credencial e confirmar heartbeat antes de encerrar incidente.

## Revogação de edge workers
1. Identificar `worker_id`, organização, site e câmeras afetadas.
2. Revogar credencial na API/admin operacional.
3. Confirmar que heartbeat/detections antigas são rejeitados.
4. Coletar buffer offline local antes de apagar dispositivo, se houver investigação pendente.
5. Emitir nova credencial somente para dispositivo validado.

## Runbooks de incidente operacional
### API degradada
- Checar `/api/v1/health`, `/api/v1/readiness` e `/api/v1/metrics`.
- Verificar logs com `request_id` e erros de database/redis/storage.
- Se apenas Web falhar, manter API e edge workers ativos.
- Se API rejeitar mutações por CSRF/origin, conferir domínio e `allowed_origins`.

### PostgreSQL indisponível
- API deve ficar degraded/unready.
- Pausar deploys e edge workers se houver risco de backlog excessivo.
- Restaurar serviço ou failover pelo provedor.
- Validar migrations e consultas de incidente após retorno.

### MinIO/S3 indisponível
- Incidentes podem continuar sem evidência binária completa, conforme fluxo atual.
- Dashboard deve mostrar estado vazio/erro de evidência sem quebrar triagem.
- Não apagar metadados de evidência para “corrigir” falha de storage.
- Após retorno, validar URLs assinadas e bucket privado.

### Redis indisponível
- Rate limit compartilhado pode ficar degradado.
- Em staging/prod, não cair silenciosamente para `memory` sem decisão explícita.
- Recriar Redis e validar `/metrics` e login.

### Worker offline em massa
- Checar conectividade com API e credenciais do worker.
- Usar `python -m vigia_edge_worker.main --diagnose` no host/container.
- Verificar `pending_queue`, `last_error`, `cv_mode` e `source_type` no heartbeat.
- Preservar `EDGE_BUFFER_PATH` antes de redeploy destrutivo.

## Obrigatório antes de produção
- Backup automatizado PostgreSQL com restore testado.
- Backup/replicação de bucket de evidências.
- Secret manager com rotação documentada.
- Smoke de restore periódico em ambiente isolado.
- Runbook de incidente operacional conhecido pelo time.
- Contato de suporte e janela de manutenção definidos.
