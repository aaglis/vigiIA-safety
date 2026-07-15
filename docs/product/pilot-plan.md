# Plano de piloto e critérios de pronto para cliente

## Objetivo
Definir quando o VigIA Safety pode ser apresentado em piloto controlado sem prometer capacidades fora do estado atual do produto.

O piloto valida o ciclo: **detecção controlada → incidente → evidência → triagem humana → auditoria → métricas**.

## Cenários suportados no piloto
- Uma organização de staging dedicada.
- Um site piloto por vez.
- Uma a três câmeras, vídeos locais ou fontes controladas por ambiente.
- Edge worker em modo `CV_MODE=mock` para demonstração determinística ou `CV_MODE=real` com marker/dataset controlado.
- Zonas de risco cadastradas e associadas a câmera/site.
- Detecções-alvo iniciais:
  - pessoa em zona de risco;
  - capacete;
  - colete de segurança.
- Volume inicial: baixo a moderado, com execução acompanhada pelo time técnico.
- Evidência visual por snapshot/metadata quando disponível; clipes completos permanecem limitados ao fluxo aprovado.

## Fora do escopo do piloto
- Reconhecimento facial, identificação biométrica ou tracking individual.
- Gravação contínua sem evento.
- WhatsApp real, ligações automáticas ou notificações externas críticas.
- Analytics avançado multi-site, ranking de produtividade ou avaliação individual.
- Alto volume multi-site/multi-câmera sem acompanhamento técnico.
- SLA formal de produção.
- Treinamento customizado de modelo em dados do cliente sem contrato, autorização e pipeline próprios.
- Acesso de suporte a evidências fora do fluxo tenant-scoped e auditado.

## Roteiro de demonstração
1. Acessar a Web staging por HTTPS.
2. Fazer login com usuário autorizado de staging.
3. Abrir dashboard e confirmar organização/site corretos.
4. Rodar edge worker controlado:
   - mock determinístico para demo rápida; ou
   - real adapter com frame/vídeo local aprovado.
5. Confirmar heartbeat/telemetria do worker.
6. Confirmar criação ou reaproveitamento idempotente do incidente.
7. Abrir detalhe do incidente no dashboard.
8. Revisar evidência visual ou estado vazio quando não houver snapshot/clip.
9. Conferir confiança, modelo, câmera, zona, site e timestamp.
10. Reconhecer o incidente.
11. Resolver ou descartar com justificativa operacional quando aplicável.
12. Conferir trilha de auditoria e métricas.

## Métricas de sucesso
Use os números como critérios iniciais de beta, não como SLA de produção.

| Métrica | Critério inicial |
| --- | --- |
| Latência edge → incidente | alvo ≤ 5s em cenário controlado; investigar acima de 10s |
| Tempo até reconhecimento | operador reconhece incidente em até 2 minutos durante demo assistida |
| Falso positivo | ≤ 10% nos cenários controlados do piloto |
| Falso negativo | nenhum falso negativo crítico aceito em zona de risco durante demo controlada |
| Disponibilidade do worker | heartbeat recente e `pending_queue` estável/zerando quando API disponível |
| Evidência | snapshot/link seguro disponível quando o evento tiver evidência registrada |
| Auditoria | 100% das ações de reconhecer/resolver/descartar aparecem na trilha |
| Segurança | sem URL assinada exposta antes de ação explícita no dashboard |

## Checklist pré-piloto
- [ ] Runbook de staging seguido: [`docs/deployment/staging-pilot.md`](../deployment/staging-pilot.md).
- [ ] `APP_ENV=staging`, `REPOSITORY_BACKEND=postgres` e rate limit com Redis.
- [ ] Secrets configurados fora do repo e sem placeholders/dev-only.
- [ ] `bash scripts/check-secrets.sh` e `bash scripts/validate.sh` passam na revisão que será demonstrada.
- [ ] Health/readiness/metrics da API staging saudáveis.
- [ ] Migrations aplicadas e seed/demo aprovado quando necessário.
- [ ] Usuários e permissões do piloto revisados.
- [ ] Painel de configuração operacional revisado com `site_id`, `camera_id` e `zone_id` do tenant ativo.
- [ ] Regras e EPIs do catálogo conferidos contra o cenário que o edge worker vai monitorar.
- [ ] Edge worker com credencial própria de staging.
- [ ] Fonte de câmera/vídeo aprovada e sem material sensível desnecessário.
- [ ] Consentimento/comunicação LGPD definidos para qualquer dado real.
- [ ] Bucket de evidências privado e retenção alinhada ao piloto.
- [ ] Plano de backup mínimo do banco e evidências definido.
- [ ] Contato de suporte técnico e janela de observação combinados.
- [ ] Plano de rollback conhecido pelo responsável técnico.

## Critérios de go/no-go

### Go
- Staging saudável com HTTPS, Postgres, Redis e storage privado.
- Smoke pós-deploy concluído sem falha crítica.
- Edge worker publica heartbeat e detecção controlada.
- Configuração operacional do dashboard lista site, câmera e zona usados pelo worker.
- Incidente aparece no dashboard com contexto de câmera/zona/site.
- Evidência visual ou estado vazio aparece corretamente.
- Ações de triagem geram auditoria.
- Métricas do dataset sintético e telemetria do worker estão disponíveis.
- Responsável pelo cliente entende limites do piloto e fora de escopo.

### No-go
- Qualquer secret real aparece em repo, log compartilhado, card ou chat.
- Staging usa backend `memory` ou credenciais dev-only.
- Health/readiness degradado sem explicação.
- Worker sem heartbeat confiável ou fila offline crescendo sem drenar.
- Incidentes aparecem em organização/site incorreto.
- Evidências vazam por URL pública não assinada ou sem permissão.
- Demo depende de dado pessoal real sem aprovação/LGPD.
- Taxa de falso positivo/negativo inviabiliza a narrativa de segurança.

## Riscos conhecidos e mitigação
- **Detector inicial ainda é adapter leve**: usar cenário controlado, dataset sintético e comunicar limite.
- **RTSP real ainda é experimental**: preferir arquivo/vídeo local ou fonte controlada.
- **Evidência binária completa ainda evolui**: validar metadata/snapshot/link seguro disponível no fluxo atual.
- **Sem SLA de produção**: classificar como piloto assistido, com acompanhamento técnico.
- **Dados sensíveis**: aplicar minimização, retenção e acesso tenant-scoped.

## Documentos relacionados
- Escopo MVP: [`mvp-scope.md`](./mvp-scope.md)
- Métricas de validação: [`validation-metrics.md`](./validation-metrics.md)
- Checklist de readiness beta: [`../customer/beta-readiness-checklist.md`](../customer/beta-readiness-checklist.md)
- Staging/piloto: [`../deployment/staging-pilot.md`](../deployment/staging-pilot.md)
- CI e gates: [`../deployment/ci.md`](../deployment/ci.md)
- Observabilidade: [`../deployment/observability.md`](../deployment/observability.md)
- LGPD/privacidade: [`../security/lgpd-privacy-strategy.md`](../security/lgpd-privacy-strategy.md)
- Threat model multi-tenant: [`../security/tenant-isolation-threat-model.md`](../security/tenant-isolation-threat-model.md)
- Retenção/auditoria: [`../security/lgpd-audit-retention-policy.md`](../security/lgpd-audit-retention-policy.md)
