# Proposta operacional de POC assistida

## Objetivo

Este documento estrutura uma POC assistida do VigIA Safety para validar valor operacional com um cliente sem posicionar o produto como SaaS de produção. A proposta deve ser usada junto com contrato, aceite jurídico/LGPD e checklist de readiness; ela não define preço, SLA ou obrigação de produção.

## Posicionamento correto

O VigIA Safety, neste estágio, deve ser oferecido como:

- POC assistida;
- piloto beta controlado;
- validação com design partner;
- demonstração operacional com humano no loop.

Não deve ser vendido nesta etapa como:

- SaaS produtivo autônomo;
- sistema com SLA formal;
- solução de decisão automática de segurança;
- monitoramento biométrico ou identificação individual;
- substituto de equipe, CIPA, SESMT, auditoria humana ou procedimentos internos do cliente.

## Escopo da POC

Durante a POC, o cliente valida o ciclo:

**detecção controlada → incidente → evidência sob demanda → triagem humana → auditoria → feedback operacional**.

### Incluído

- Ambiente de staging/piloto dedicado ou logicamente isolado.
- Login web para usuários autorizados.
- Dashboard de incidentes com filtros por status, severidade, site, câmera, zona e período.
- Configuração operacional de site, câmera, zona, regra e EPI combinados.
- Edge worker em cenário controlado, com `CV_MODE=mock` ou `CV_MODE=real` limitado conforme aceite.
- Evidência visual quando disponível, acessada por URL assinada sob demanda.
- Ações de triagem: reconhecer, resolver ou descartar.
- Auditoria das ações relevantes.
- Health/readiness/métricas operacionais protegidas.
- Suporte assistido durante janela combinada.

### Fora do escopo

- Produção 24/7.
- SLA, SLO contratual ou disponibilidade mínima.
- Reconhecimento facial, biometria, identificação individual ou tracking pessoal.
- Medição de produtividade ou ranking de trabalhadores.
- Gravação contínua sem evento de risco.
- Alertas externos críticos, ligações automáticas ou WhatsApp real sem contrato específico.
- Alto volume multi-site/multi-câmera sem novo planejamento técnico.
- Treinamento de modelo com dados do cliente sem autorização, contrato e pipeline próprios.
- Acesso de suporte a evidências fora de fluxo tenant-scoped e auditado.

## Pré-requisitos para iniciar

### Responsáveis

O cliente deve indicar:

- responsável operacional;
- responsável técnico;
- ponto focal de privacidade/LGPD;
- usuários autorizados e papéis esperados;
- canal de suporte durante a janela assistida.

O time VigIA deve indicar:

- responsável pela execução técnica;
- responsável por segurança/privacidade da POC;
- responsável por rollback/pausa;
- responsável por registrar achados e decisão go/no-go.

### Dados e ambiente

Antes da POC, confirmar:

- organização/unidade piloto;
- um site piloto;
- uma a três câmeras ou fontes controladas;
- zonas de risco e regras operacionais;
- EPIs esperados por zona/regra, quando aplicável;
- período de retenção de evidências;
- fonte de vídeo/câmera aprovada e minimizada ao necessário;
- comunicação/consentimento quando houver dado real de pessoas.

Não enviar senhas, tokens, chaves de API, cookies, URLs assinadas, credenciais SMTP/storage ou dados pessoais sensíveis por chat, card, e-mail comum ou documento compartilhado. Segredos devem entrar apenas pelo canal seguro aprovado ou secret manager.

## Segurança, LGPD e retenção

A POC só deve avançar quando:

- `docs/customer/beta-readiness-checklist.md` estiver preenchido para go/no-go;
- `bash scripts/validate.sh` e `bash scripts/check-secrets.sh` passarem na revisão candidata;
- staging seguir `docs/deployment/staging-pilot.md`;
- `scripts/staging-smoke.sh` for executado contra URLs reais com variáveis `STAGING_*` vindas de secret manager;
- evidências estiverem em bucket privado;
- URLs assinadas só forem geradas sob demanda;
- retenção de evidências estiver alinhada ao piloto;
- permissões do usuário estiverem limitadas ao tenant e papel acordados;
- não houver dado real sem base legal/comunicação aplicável.

Referências:

- LGPD/privacidade: [`../security/lgpd-privacy-strategy.md`](../security/lgpd-privacy-strategy.md)
- Auditoria e retenção: [`../security/lgpd-audit-retention-policy.md`](../security/lgpd-audit-retention-policy.md)
- Evidências: [`../security/evidence-retention.md`](../security/evidence-retention.md)
- Segredos: [`../security/secret-management-policy.md`](../security/secret-management-policy.md)
- Isolamento tenant: [`../security/tenant-isolation-threat-model.md`](../security/tenant-isolation-threat-model.md)

## Critérios de sucesso

A POC é considerada tecnicamente bem-sucedida quando:

- ambiente staging está saudável em HTTPS, com Postgres, Redis/rate limit e storage privado;
- edge worker publica heartbeat e envia detecção controlada;
- incidente aparece no tenant/site/câmera/zona corretos;
- dashboard permite filtrar e abrir detalhe do incidente;
- evidência aparece somente quando solicitada por ação explícita;
- reconhecer/resolver/descartar gera auditoria;
- logs compartilháveis não contêm secrets, cookies, headers sensíveis ou URL assinada;
- responsável operacional do cliente consegue avaliar se o fluxo serve ao processo real;
- limitações conhecidas ficam documentadas antes de qualquer próximo passo.

Critérios iniciais de referência vêm de [`../product/pilot-plan.md`](../product/pilot-plan.md). Eles não são SLA de produção.

## Critérios de no-go ou pausa

Pausar ou bloquear a POC se ocorrer:

- secret real em repositório, log compartilhado, print, card ou chat;
- staging usando backend `memory`, credenciais dev-only ou bucket público;
- incidente/evidência/auditoria aparecendo fora da organização correta;
- URL assinada aparecendo antes do clique explícito ou em logs compartilhados;
- câmera real/dado pessoal sem aprovação ou comunicação aplicável;
- worker sem heartbeat confiável ou fila offline crescendo sem drenar;
- health/readiness quebrado sem mitigação aceita;
- cliente esperar produção, SLA, automação crítica ou uso fora do escopo.

## Agenda sugerida

1. Confirmar escopo, responsáveis, limites e fora de escopo.
2. Revisar checklist de readiness e resultado dos smokes.
3. Acessar a Web staging autorizada.
4. Confirmar organização, usuários e permissões.
5. Revisar site, câmera, zona, regra e EPI.
6. Rodar edge worker em cenário controlado.
7. Verificar heartbeat, incidente e filtros.
8. Abrir detalhe e evidência sob demanda.
9. Executar triagem: reconhecer, resolver ou descartar.
10. Conferir auditoria, métricas e logs sanitizados.
11. Registrar feedback operacional e decisão de próximo passo.

## Como reportar problemas

Relatos devem incluir:

- data/hora aproximada;
- ambiente usado;
- usuário ou perfil operacional, sem senha;
- site/câmera/zona;
- ação realizada;
- comportamento observado;
- comportamento esperado;
- impacto operacional;
- evidência não sensível.

Não incluir:

- prints com pessoas identificáveis;
- URL assinada;
- tokens, cookies, headers ou chaves;
- logs completos com query string sensível;
- dados pessoais desnecessários.

## Entregáveis ao final

Ao final da POC, consolidar:

- decisão: avançar, repetir, pausar ou encerrar;
- achados técnicos;
- achados operacionais;
- riscos de segurança/LGPD;
- limitações aceitas;
- backlog recomendado;
- critérios para nova POC ou contrato futuro.

Qualquer avanço para produção exige contrato, revisão de segurança, revisão LGPD, plano operacional, backup/restore validado, suporte definido e aceite explícito das partes.

## Referências

- Handoff beta: [`./beta-handoff.md`](./beta-handoff.md)
- Readiness beta: [`./beta-readiness-checklist.md`](./beta-readiness-checklist.md)
- Plano de piloto: [`../product/pilot-plan.md`](../product/pilot-plan.md)
- Staging: [`../deployment/staging-pilot.md`](../deployment/staging-pilot.md)
- CI e gates: [`../deployment/ci.md`](../deployment/ci.md)
- Backup/restore: [`../deployment/backup-restore.md`](../deployment/backup-restore.md)
- Baseline de volume: [`../deployment/incident-volume-baseline.md`](../deployment/incident-volume-baseline.md)
