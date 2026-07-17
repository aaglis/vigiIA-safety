# Readiness Cliente 1 / POC 1

## Objetivo

Registrar a decisão go/no-go interna para a primeira POC assistida do VigIA Safety, sem incluir segredos, URLs assinadas, cookies, headers, imagens reais, dados pessoais ou informações identificáveis do cliente.

Este registro complementa o template [`beta-readiness-checklist.md`](./beta-readiness-checklist.md) e deve ser revisado antes de qualquer sessão com cliente real.

## Decisão atual

**Status:** Pendente aceito para preparação interna; **No-go para sessão com cliente real** até concluir os itens manuais e os smokes que dependem de credenciais/ambiente seguro.

**Motivo:** o ambiente PDC/Web/API está funcional e os smokes isolados de backup/restore e volume passaram, mas ainda faltam validações de staging com `STAGING_*`, edge worker controlado e evidência/auditoria ponta a ponta com tenant real/controlado.

**Responsáveis internos:** Produto, Engenharia, Operação e Privacidade.

**Cliente:** Cliente 1 / POC 1, sem identificação nominal neste documento.

## Resumo por área

| Área | Status | Evidência segura | Próximo passo |
| --- | --- | --- | --- |
| Produto/escopo | Pendente aceito | Proposta e handoff existem; escopo beta assistido documentado. | Revisar limites com o responsável do cliente antes da sessão. |
| Ambiente PDC | Go técnico inicial | URL pública responde; `/api/v1/health` e `/api/v1/readiness` retornaram `200`; `/api/v1/auth/me` retornou `401` sem token, esperado. | Repetir smoke após qualquer deploy. |
| Secrets | Go técnico inicial | Env keys obrigatórias no PDC estavam presentes e não vazias; nenhum valor foi exposto. | Confirmar rotação/governança no painel seguro. |
| Staging smoke | Pendente | `scripts/staging-smoke.sh` requer `STAGING_API_BASE_URL`, `STAGING_WEB_BASE_URL` e `STAGING_METRICS_TOKEN` vindos de ambiente seguro. | Rodar com variáveis fora do chat e registrar apenas saída sanitizada. |
| Edge worker staging | Pendente | Worker tem diagnose/heartbeat/buffer offline documentados; staging real ainda não comprovado nesta revisão. | Rodar diagnose e detecção controlada com credencial técnica. |
| Evidência/auditoria staging | Pendente | Fluxos locais e componentes de dashboard existem; validação real com tenant/controlado ainda não concluída. | Validar incidente controlado, evidência sob demanda e auditoria. |
| Backup/restore | Go técnico inicial | Restore isolado PostgreSQL + MinIO passou com dados demo e sem segredos. | Repetir periodicamente e antes de dados reais. |
| Volume sintético | Go técnico inicial | Postgres isolado com 1k incidentes sintéticos mediu filtros/listagem/detalhe/auditoria/evidência com latências abaixo de 100ms. | Repetir com volume maior se a POC exigir escala maior. |
| UI pós-login | Go para demo interna | Shell autenticado, sidebar e dashboard operacional foram implementados; ainda há placeholders em recursos administrativos. | Completar CRUDs de organizações, usuários e operações antes de vender como produto completo. |
| LGPD/privacidade | Pendente | Políticas e runbooks existem; aprovação do caso real ainda depende do cliente. | Confirmar finalidade, minimização, comunicação e retenção. |
| Operação/suporte | Pendente | Runbooks de staging, backup/restore e observabilidade existem. | Definir janela assistida, canal de suporte e responsáveis. |

## Evidências técnicas já registradas

- Deploy PDC Web/API funcional em HTTPS público, sem registrar segredos.
- Health/readiness respondendo `200` na API pública.
- Métricas protegidas documentadas; validação com token depende de `STAGING_METRICS_TOKEN` fora do chat.
- `bash scripts/check-secrets.sh`: OK na revisão local.
- `bash scripts/intelliboard-validate.sh`: OK na revisão local.
- `bash scripts/backup-restore-smoke.sh`: OK em Compose isolado.
- `bash scripts/postgres-volume-smoke.sh`: OK em Postgres isolado com 1k incidentes sintéticos após bootstrap do catálogo mínimo.

## Pendências bloqueantes para cliente real

1. Rodar `scripts/staging-smoke.sh` com `STAGING_*` obtidos do painel/secret manager, sem colar valores em chat/card.
2. Validar edge worker em staging com credencial técnica própria, heartbeat e detecção controlada idempotente.
3. Validar evidência e auditoria ponta a ponta com incidente controlado.
4. Confirmar usuário/tenant correto para a sessão assistida.
5. Confirmar aprovação de privacidade/LGPD quando houver câmera, imagem ou dado real.
6. Combinar janela assistida, canal de suporte, rollback/pausa e responsáveis.

## Critério de mudança para Go

Alterar este registro para **Go** somente quando:

- todos os itens técnicos pendentes acima tiverem evidência sanitizada;
- o cliente tiver aceitado escopo beta assistido e fora de escopo;
- não houver secrets, dados pessoais sensíveis ou URLs assinadas em logs compartilhados;
- health/readiness/metrics estiverem saudáveis ou com degradação aceita;
- a equipe souber pausar worker/API/Web e acionar rollback.

## Referências

- [`beta-readiness-checklist.md`](./beta-readiness-checklist.md)
- [`poc-assisted-proposal.md`](./poc-assisted-proposal.md)
- [`beta-handoff.md`](./beta-handoff.md)
- [`../deployment/staging-pilot.md`](../deployment/staging-pilot.md)
- [`../deployment/backup-restore.md`](../deployment/backup-restore.md)
- [`../deployment/incident-volume-baseline.md`](../deployment/incident-volume-baseline.md)
