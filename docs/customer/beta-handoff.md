# Pacote de handoff do piloto beta

Este documento resume o que será entregue ao cliente beta no piloto assistido do VigIA Safety. A linguagem é operacional e evita detalhes internos de infraestrutura, segredos, credenciais ou promessas de SLA.

## 1. Objetivo do piloto

Validar, em ambiente controlado, o ciclo:

**detecção controlada → incidente → evidência → triagem humana → auditoria → métricas operacionais**.

O piloto serve para confirmar aderência do fluxo ao processo de segurança do trabalho do cliente, levantar ajustes de operação e medir riscos conhecidos antes de qualquer discussão de produção.

## 2. Escopo entregue ao cliente beta

Durante o piloto, o cliente terá acesso acompanhado a:

- login web para usuários autorizados;
- dashboard de incidentes com filtros por status, severidade, site, câmera, zona e período;
- painel de configuração operacional para revisar sites, câmeras, zonas, regras e EPIs cadastrados;
- geração de incidente por edge worker em cenário controlado;
- evidência visual por snapshot quando disponível;
- abertura de evidência por URL segura e sob demanda;
- ações de triagem: reconhecer, resolver ou descartar incidente com justificativa;
- trilha de auditoria das ações relevantes;
- métricas básicas de saúde, prontidão e operação do ambiente.

## 3. O que não será testado

Ficam fora do piloto beta:

- reconhecimento facial, biometria ou identificação individual;
- ranking, medição de produtividade ou avaliação individual de trabalhadores;
- gravação contínua por padrão sem evento de risco;
- WhatsApp real, ligações automáticas ou alertas externos críticos;
- SLA formal de produção;
- alto volume multi-site/multi-câmera sem acompanhamento técnico;
- treinamento customizado de modelo com dados do cliente sem contrato, autorização e pipeline próprios;
- acesso de suporte a evidências fora do fluxo tenant-scoped e auditado.

## 4. Responsabilidades

### Time VigIA Safety

- Preparar ambiente de staging/piloto e executar validações antes da sessão.
- Configurar usuários, permissões, sites, câmeras, zonas, regras e EPIs combinados.
- Acompanhar a execução assistida e registrar incidentes técnicos.
- Orientar triagem, evidência, auditoria e limites do piloto.
- Apoiar rollback ou pausa do piloto se houver risco operacional, privacidade ou segurança.

### Cliente beta

- Indicar responsável operacional, responsável técnico e ponto focal de privacidade/LGPD.
- Aprovar cenário, fonte de vídeo/câmera e áreas monitoradas.
- Confirmar comunicação/consentimento aplicáveis antes de qualquer dado real.
- Validar se os incidentes exibidos fazem sentido para o processo operacional.
- Reportar problemas com horário aproximado, site/câmera/zona e ação realizada.

## 5. Dados e acessos necessários

Antes da sessão, confirmar:

- nome da organização e unidade piloto;
- lista de usuários autorizados e papéis esperados;
- um site piloto;
- uma a três câmeras ou fontes controladas;
- zonas monitoradas e regra operacional associada;
- EPIs esperados por zona/regra, quando aplicável;
- período de retenção desejado para evidências do piloto;
- contato de suporte e janela de acompanhamento.

Não enviar senhas, tokens, chaves de API, credenciais SMTP, credenciais de storage ou dados pessoais sensíveis por chat, card ou documento compartilhado. Credenciais devem ser configuradas apenas por canal seguro aprovado.

## 6. Checklist LGPD, privacidade e retenção

- [ ] Finalidade do piloto explicada aos envolvidos.
- [ ] Comunicação/consentimento definidos quando houver dado real de pessoas.
- [ ] Fonte de vídeo/câmera aprovada e minimizada ao necessário.
- [ ] Sem reconhecimento facial ou identificação biométrica.
- [ ] Sem uso para produtividade individual.
- [ ] Evidências acessíveis apenas por usuários autorizados do tenant.
- [ ] URLs de evidência geradas apenas sob demanda.
- [ ] Retenção de snapshots/evidências alinhada ao piloto.
- [ ] Processo de exclusão/expurgo conhecido pelo responsável do cliente.
- [ ] Incidentes e ações relevantes aparecem em auditoria.

## 7. Agenda sugerida da sessão assistida

1. Confirmar escopo, responsáveis e limites do piloto.
2. Acessar o ambiente web autorizado.
3. Revisar configuração operacional: site, câmera, zona, regra e EPI.
4. Executar detecção controlada pelo edge worker.
5. Conferir criação do incidente no dashboard.
6. Aplicar filtros de triagem para localizar o incidente.
7. Abrir detalhe, evidência e contexto técnico disponível.
8. Reconhecer o incidente.
9. Resolver ou descartar com justificativa operacional.
10. Revisar auditoria, métricas e observações.
11. Registrar feedback, ajustes e decisão de próximo passo.

## 8. Smoke/checklist antes do handoff

O time VigIA deve validar antes de envolver o cliente:

- [ ] `bash scripts/validate.sh` passou na revisão que será demonstrada.
- [ ] Staging segue o runbook de piloto e não usa backend `memory`.
- [ ] Health, readiness e métricas da API estão saudáveis ou com degradação explicada.
- [ ] Usuário do cliente consegue autenticar no tenant correto.
- [ ] Catálogo operacional mostra site, câmera e zona esperados.
- [ ] Edge worker publica heartbeat e envia detecção controlada.
- [ ] Incidente aparece no dashboard com filtros funcionando.
- [ ] Evidência visual aparece quando habilitada e disponível.
- [ ] Ações de triagem geram auditoria.
- [ ] Plano de rollback/pausa é conhecido pelo time técnico.

## 9. Como reportar problemas

Ao reportar um problema, incluir:

- data e horário aproximado;
- ambiente usado;
- usuário ou perfil operacional envolvido, sem senha;
- site, câmera e zona, se aplicável;
- ação realizada;
- comportamento observado;
- comportamento esperado;
- impacto operacional;
- evidência não sensível, se houver.

Não incluir prints com pessoas identificáveis, URLs assinadas de evidência, tokens, headers, cookies ou chaves de API.

## 10. Suporte e operação durante o piloto

- O piloto é assistido: incidentes críticos de operação devem ser comunicados ao ponto focal combinado.
- Falhas de notificação externa não bloqueiam a triagem no dashboard.
- Em caso de risco de privacidade, exposição indevida de evidência ou comportamento fora do escopo, pausar o piloto e acionar o responsável VigIA.
- Backups, restore e rollback seguem runbooks internos, sem exposição de credenciais ao cliente.

## 11. Documentos relacionados

- Proposta de POC assistida: [`./poc-assisted-proposal.md`](./poc-assisted-proposal.md)
- Plano de piloto: [`../product/pilot-plan.md`](../product/pilot-plan.md)
- Checklist de readiness beta: [`./beta-readiness-checklist.md`](./beta-readiness-checklist.md)
- Escopo MVP: [`../product/mvp-scope.md`](../product/mvp-scope.md)
- Staging/piloto: [`../deployment/staging-pilot.md`](../deployment/staging-pilot.md)
- Smoke local/CI: [`../deployment/ci.md`](../deployment/ci.md)
- Observabilidade: [`../deployment/observability.md`](../deployment/observability.md)
- Backup e restore: [`../deployment/backup-restore.md`](../deployment/backup-restore.md)
- Privacidade/LGPD: [`../security/lgpd-privacy-strategy.md`](../security/lgpd-privacy-strategy.md)
- Auditoria e retenção: [`../security/lgpd-audit-retention-policy.md`](../security/lgpd-audit-retention-policy.md)
- Retenção de evidências: [`../security/evidence-retention.md`](../security/evidence-retention.md)
- Acesso e auditoria: [`../security/access-audit-policy.md`](../security/access-audit-policy.md)
- Política de notificações: [`../architecture/notification-policy.md`](../architecture/notification-policy.md)
- Catálogo operacional: [`../architecture/operations-catalog-mvp.md`](../architecture/operations-catalog-mvp.md)

## 12. Declaração de limite

Este handoff não cria obrigação de produção, SLA, disponibilidade mínima ou suporte 24/7. Qualquer avanço para produção exige contrato, revisão de segurança, revisão LGPD, plano operacional e aceite explícito das partes.
