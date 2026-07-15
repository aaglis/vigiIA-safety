# Checklist de readiness beta

## Objetivo

Consolidar a decisão go/no-go antes de envolver um cliente beta no piloto assistido do VigIA Safety. Este checklist não substitui contrato, avaliação jurídica, revisão de segurança ou aceite do cliente; ele reúne os sinais mínimos para decidir se a sessão pode acontecer com risco controlado.

Use este documento na reunião interna de readiness e atualize o estado de cada item como:

- **Go**: pronto para a sessão;
- **Pendente aceito**: pendência conhecida, com responsável e mitigação explícita;
- **No-go**: bloqueia o beta até correção.

Não registre senhas, tokens, URLs assinadas, cookies, headers, chaves de API ou dados pessoais sensíveis neste checklist.

## Resumo de decisão

| Área | Tipo | Responsável | Status | Evidência segura |
| --- | --- | --- | --- | --- |
| Produto/escopo | Manual | Product + cliente | ☐ Go ☐ Pendente ☐ No-go | Escopo e limites revisados com [`pilot-plan.md`](../product/pilot-plan.md) e [`beta-handoff.md`](./beta-handoff.md) |
| Ambiente staging | Técnico/manual | Engenharia | ☐ Go ☐ Pendente ☐ No-go | Runbook [`staging-pilot.md`](../deployment/staging-pilot.md) seguido sem backends `memory` |
| Gates automatizados | Automático | Engenharia | ☐ Go ☐ Pendente ☐ No-go | `validate.sh`, `check-secrets.sh`, smoke/e2e aplicável executados |
| Segurança e acesso | Técnico/manual | Engenharia + segurança | ☐ Go ☐ Pendente ☐ No-go | RBAC, tenant isolation, CSRF/CORS/rate limit e evidência sob demanda conferidos |
| LGPD/privacidade | Jurídico/manual | Cliente + privacidade | ☐ Go ☐ Pendente ☐ No-go | Finalidade, comunicação, minimização e retenção aprovadas |
| Operação e suporte | Manual | Operação + cliente | ☐ Go ☐ Pendente ☐ No-go | Janela assistida, responsáveis, rollback e reporte combinados |
| Dados e evidências | Técnico/jurídico | Engenharia + privacidade | ☐ Go ☐ Pendente ☐ No-go | Fonte de vídeo/câmera aprovada e sem material sensível desnecessário |

## Go/no-go rápido

### Go

Avançar para beta assistido somente se todos os itens abaixo estiverem verdadeiros:

- ambiente de staging em HTTPS, com PostgreSQL, Redis/rate limit e storage privado;
- secrets fora do repositório e sem placeholders/dev-only;
- health/readiness/metrics saudáveis ou com degradação documentada e aceita;
- edge worker com credencial própria, heartbeat confiável e detecção controlada;
- dashboard mostra organização, site, câmera, zona, incidente, evidência/estado vazio e auditoria corretos;
- evidência visual só é solicitada por ação explícita e usa URL assinada curta;
- permissões do usuário beta limitadas ao tenant e papel combinado;
- LGPD/privacidade: finalidade, comunicação/consentimento e retenção definidos quando houver dado real;
- cliente entende o que está fora do piloto e que não há SLA formal de produção;
- rollback/pausa e canal de suporte assistido estão combinados.

### No-go automático

Bloquear ou pausar o beta se qualquer item ocorrer:

- secret real em repositório, log compartilhado, card, chat, print ou relatório;
- staging usando `REPOSITORY_BACKEND=memory`, `RATE_LIMIT_BACKEND=memory`, credenciais dev-only ou bucket público;
- incidente, evidência, auditoria ou usuário aparece fora da organização correta;
- URL assinada aparece antes do clique explícito ou em logs compartilhados;
- dado pessoal real, câmera real ou imagem identificável sem aprovação/comunicação aplicável;
- worker sem heartbeat confiável, fila offline crescendo sem drenar ou fonte de vídeo não aprovada;
- health/readiness quebrado sem mitigação;
- falso positivo/negativo inviabiliza a narrativa de segurança no cenário controlado;
- cliente espera produção, SLA, automação crítica externa ou uso fora do escopo.

## Checklist detalhado

### 1. Produto e escopo

| Item | Tipo | Status | Referência |
| --- | --- | --- | --- |
| Ciclo do piloto confirmado: detecção controlada → incidente → evidência → triagem → auditoria → métricas. | Manual | ☐ | [`pilot-plan.md`](../product/pilot-plan.md) |
| Fora de escopo revisado: biometria, produtividade individual, gravação contínua, alertas externos críticos e SLA formal. | Manual/cliente | ☐ | [`beta-handoff.md`](./beta-handoff.md) |
| Cliente indicou responsável operacional, técnico e ponto focal LGPD/privacidade. | Cliente | ☐ | [`beta-handoff.md`](./beta-handoff.md) |
| Roteiro assistido e critérios de sucesso entendidos como beta, não SLA. | Manual/cliente | ☐ | [`pilot-plan.md`](../product/pilot-plan.md) |
| Proposta de POC assistida revisada sem promessa de produção/SLA. | Manual/cliente | ☐ | [`poc-assisted-proposal.md`](./poc-assisted-proposal.md) |

### 2. Ambiente e deploy

| Item | Tipo | Status | Referência |
| --- | --- | --- | --- |
| Staging usa HTTPS, Postgres, Redis/rate limit e storage privado. | Técnico/manual | ☐ | [`staging-pilot.md`](../deployment/staging-pilot.md) |
| Plano de provisionamento de staging foi seguido ou marcado como pendente/no-go. | Técnico/manual | ☐ | [`staging-provisioning-plan.md`](../deployment/staging-provisioning-plan.md) |
| `APP_ENV=staging`, `REPOSITORY_BACKEND=postgres` e backend de rate limit não-memory. | Técnico/manual | ☐ | [`environment-separation.md`](../security/environment-separation.md) |
| Secrets configurados apenas em secret manager/painel aprovado. | Manual | ☐ | [`secret-management-policy.md`](../security/secret-management-policy.md) |
| Migrations aplicadas e seed/demo aprovado quando necessário. | Técnico/manual | ☐ | [`staging-pilot.md`](../deployment/staging-pilot.md) |
| Health, readiness e metrics conferidos sem exposição de segredos. | Técnico/manual | ☐ | [`observability.md`](../deployment/observability.md) |

### 3. Gates automatizados e smokes

| Item | Tipo | Status | Referência |
| --- | --- | --- | --- |
| `bash scripts/validate.sh` passou na revisão candidata. | Automático | ☐ | [`ci.md`](../deployment/ci.md) |
| `bash scripts/check-secrets.sh` passou sem achados fora da allowlist. | Automático | ☐ | [`secret-handling-checklist.md`](../deployment/secret-handling-checklist.md) |
| `bash scripts/staging-smoke.sh` rodou contra staging real com `STAGING_*` via secret manager e sem imprimir segredos. | Automático/manual | ☐ | [`staging-pilot.md`](../deployment/staging-pilot.md) |
| E2E browser validou login, triagem e evidência somente sob demanda. | Automático | ☐ | [`ci.md`](../deployment/ci.md) |
| Smoke local/CI ou staging executado conforme ambiente da sessão. | Automático/manual | ☐ | [`staging-pilot.md`](../deployment/staging-pilot.md) |
| Volume sintético de incidentes revisado para filtros do dashboard. | Automático/manual | ☐ | [`incident-volume-baseline.md`](../deployment/incident-volume-baseline.md) |

### 4. Segurança, permissões e evidência

| Item | Tipo | Status | Referência |
| --- | --- | --- | --- |
| Usuários beta têm apenas papéis/permissões necessários. | Técnico/manual | ☐ | [`rbac-policy.md`](../security/rbac-policy.md) |
| Isolamento por organização validado para incidentes, evidências, auditoria e catálogo operacional. | Automático/técnico | ☐ | [`tenant-isolation-threat-model.md`](../security/tenant-isolation-threat-model.md) |
| CSRF/CORS/rate limit compatíveis com staging e sem bypass documentado. | Técnico/manual | ☐ | [`csrf-cors-rate-limit.md`](../security/csrf-cors-rate-limit.md) |
| Bucket de evidências privado; URLs assinadas aparecem só após clique explícito e não entram em logs compartilhados. | Técnico/manual | ☐ | [`evidence-retention.md`](../security/evidence-retention.md) |
| Ações reconhecer/resolver/descartar e acessos a evidência aparecem em auditoria. | Automático/manual | ☐ | [`access-audit-policy.md`](../security/access-audit-policy.md) |

### 5. LGPD, privacidade e retenção

| Item | Tipo | Status | Referência |
| --- | --- | --- | --- |
| Finalidade do piloto explicada aos envolvidos. | Jurídico/cliente | ☐ | [`lgpd-privacy-strategy.md`](../security/lgpd-privacy-strategy.md) |
| Comunicação/consentimento definidos quando houver dado real. | Jurídico/cliente | ☐ | [`beta-handoff.md`](./beta-handoff.md) |
| Fonte de vídeo/câmera aprovada e minimizada ao necessário. | Jurídico/cliente | ☐ | [`lgpd-audit-retention-policy.md`](../security/lgpd-audit-retention-policy.md) |
| Retenção de snapshots, clipes, metadados e audit logs alinhada ao piloto. | Jurídico/manual | ☐ | [`evidence-retention.md`](../security/evidence-retention.md) |
| Processo de pausa/expurgo conhecido caso ocorra exposição indevida. | Manual | ☐ | [`backup-restore.md`](../deployment/backup-restore.md) |

### 6. Operação, suporte e rollback

| Item | Tipo | Status | Referência |
| --- | --- | --- | --- |
| Janela assistida e canal de suporte combinados. | Manual/cliente | ☐ | [`beta-handoff.md`](./beta-handoff.md) |
| Responsáveis sabem como reportar problema sem segredos ou dados sensíveis. | Manual/cliente | ☐ | [`beta-handoff.md`](./beta-handoff.md) |
| Rollback/pausa do worker/API/Web conhecido pelo time técnico. | Técnico/manual | ☐ | [`staging-pilot.md`](../deployment/staging-pilot.md) |
| Backup/restore mínimo revisado antes de dados reais. | Técnico/manual | ☐ | [`backup-restore.md`](../deployment/backup-restore.md) |
| Jobs operacionais e observabilidade básica entendidos. | Técnico/manual | ☐ | [`operational-jobs.md`](../deployment/operational-jobs.md) |

## Exposição no dashboard/admin

Neste momento, o readiness beta fica documentado e revisado manualmente. Não há painel admin específico para status go/no-go porque parte dos itens depende de decisão humana, cliente, privacidade e configuração externa de secret manager.

Se a operação repetir o processo com múltiplos clientes, considerar um card futuro para um status interno somente leitura com: últimos gates automáticos, versão candidata, ambiente, health/readiness, smoke staging e pendências manuais. Esse painel não deve armazenar secrets nem substituir aceite jurídico/cliente.

## Registros permitidos e proibidos

Pode registrar no checklist:

- versão/branch candidata;
- data e responsável pela revisão;
- status go/pendente/no-go;
- links para runbooks, resultados de CI e tickets internos sem segredo;
- observações sem dado pessoal identificável.

Não registrar:

- senhas, tokens, API keys, cookies, headers ou credenciais SMTP/storage;
- URL assinada de evidência;
- prints com pessoas identificáveis;
- logs completos com query string sensível;
- promessa de SLA, disponibilidade mínima ou suporte 24/7.

## Referências principais

- Plano de piloto: [`../product/pilot-plan.md`](../product/pilot-plan.md)
- Handoff beta: [`./beta-handoff.md`](./beta-handoff.md)
- Proposta de POC assistida: [`./poc-assisted-proposal.md`](./poc-assisted-proposal.md)
- Staging/piloto: [`../deployment/staging-pilot.md`](../deployment/staging-pilot.md)
- Provisionamento staging: [`../deployment/staging-provisioning-plan.md`](../deployment/staging-provisioning-plan.md)
- CI e gates: [`../deployment/ci.md`](../deployment/ci.md)
- Baseline de volume: [`../deployment/incident-volume-baseline.md`](../deployment/incident-volume-baseline.md)
- Observabilidade: [`../deployment/observability.md`](../deployment/observability.md)
- Backup/restore: [`../deployment/backup-restore.md`](../deployment/backup-restore.md)
- LGPD/auditoria/retenção: [`../security/lgpd-audit-retention-policy.md`](../security/lgpd-audit-retention-policy.md)
- Threat model multi-tenant: [`../security/tenant-isolation-threat-model.md`](../security/tenant-isolation-threat-model.md)
