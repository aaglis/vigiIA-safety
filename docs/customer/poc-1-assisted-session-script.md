# Roteiro da primeira POC assistida — Cliente 1

## Objetivo da sessão

Conduzir uma POC assistida do VigIA Safety para validar se o fluxo **detecção controlada → incidente → evidência sob demanda → triagem → auditoria → decisão operacional** faz sentido para o processo real do cliente.

Este roteiro não contém preço, SLA, promessa de produção, credenciais, dados pessoais, imagens reais ou URLs assinadas. Use junto com:

- [`poc-assisted-proposal.md`](./poc-assisted-proposal.md)
- [`beta-handoff.md`](./beta-handoff.md)
- [`readiness-cliente-1-poc-1.md`](./readiness-cliente-1-poc-1.md)
- [`beta-readiness-checklist.md`](./beta-readiness-checklist.md)

## Pré-condições

Antes de iniciar com cliente real, confirmar:

- readiness Cliente 1 / POC 1 está em **Go** ou pendências foram aceitas explicitamente;
- ambiente HTTPS, health/readiness e métricas protegidas foram conferidos sem expor segredos;
- usuário/tenant da sessão foi validado;
- fonte de vídeo/cenário controlado foi aprovada;
- ninguém compartilhará tokens, senhas, cookies, headers, URLs assinadas ou prints com pessoas identificáveis;
- responsável operacional, técnico e privacidade/LGPD do cliente estão presentes ou foram indicados;
- canal de suporte, pausa/rollback e registro de achados estão combinados.

## Agenda sugerida — 60 a 75 minutos

| Tempo | Bloco | Objetivo |
| ---: | --- | --- |
| 0–5 min | Abertura | Alinhar propósito, participantes e limite beta. |
| 5–12 min | Escopo e fora de escopo | Confirmar que não é produção, SLA, vigilância individual ou substituto de processo humano. |
| 12–25 min | Demo guiada da operação | Mostrar login, dashboard, incidentes, evidências e auditoria. |
| 25–40 min | Cenário controlado | Validar o fluxo com incidente controlado ou dataset sintético aprovado. |
| 40–55 min | Validação do processo do cliente | Coletar aderência, dúvidas, riscos e lacunas. |
| 55–65 min | Privacidade e operação | Revisar minimização, retenção, suporte, rollback e responsabilidades. |
| 65–75 min | Decisão e próximos passos | Definir Go/Pendente/No-go para continuidade da POC. |

## Script de fala

### 1. Abertura

> “Hoje vamos validar o fluxo operacional do VigIA Safety em uma POC assistida. O objetivo não é prometer produção nem SLA; é entender se a triagem de incidentes com evidência e auditoria ajuda o processo de segurança do trabalho de vocês.”

Confirmar:

- quem decide valor operacional;
- quem decide privacidade/LGPD;
- quem acompanha aspectos técnicos;
- quem registra achados e decisão final.

### 2. Limites e segurança

> “Não vamos expor credenciais, tokens, URLs assinadas, imagens sensíveis ou dados pessoais desnecessários. A evidência visual deve aparecer apenas sob ação explícita e dentro do escopo aprovado.”

Reforçar fora de escopo:

- produção ou SLA formal;
- alertas externos críticos sem supervisão;
- biometria, produtividade individual ou vigilância de pessoas;
- gravação contínua fora de autorização;
- treinamento de modelo com dados reais sem contrato e pipeline próprios.

### 3. Demo guiada

Sequência recomendada:

1. Entrar no app pelo usuário/tenant combinado.
2. Mostrar o shell autenticado e o dashboard operacional.
3. Explicar KPIs: incidentes abertos, críticos, fila de ação, saúde operacional.
4. Abrir a lista de incidentes e filtros principais.
5. Selecionar um incidente controlado.
6. Mostrar detalhe: site, câmera, zona, severidade e status.
7. Solicitar evidência somente por clique explícito.
8. Mostrar auditoria e ações: reconhecer, resolver, descartar.
9. Explicar o que acontece se não houver evidência ou se storage/API estiver degradado.

### 4. Cenário controlado

Se houver edge worker/cenário aprovado:

- executar detecção controlada;
- confirmar incidente no dashboard;
- confirmar evidência ou estado vazio correto;
- reconhecer/resolver/descartar;
- conferir auditoria.

Se não houver cenário real aprovado:

- usar dataset sintético/demo;
- declarar explicitamente que a validação é de fluxo, não de precisão em ambiente real.

## Perguntas de validação

### Valor percebido

- Este fluxo ajuda a reduzir tempo de triagem?
- A evidência exibida é suficiente para decisão operacional?
- Quais campos estão faltando para contexto de segurança do trabalho?
- O dashboard mostra primeiro o que realmente importa?

### Risco e precisão

- Que falso positivo seria tolerável em POC assistida?
- Que falso negativo bloquearia continuidade?
- O que precisa ser validado antes de câmera real?
- Quais zonas/cenários têm maior valor inicial?

### Privacidade e LGPD

- A finalidade do piloto está clara para os envolvidos?
- Há necessidade de comunicação/consentimento adicional?
- O tempo de retenção de evidências está aceitável?
- Há áreas/câmeras que devem ficar fora do piloto?

### Operação e suporte

- Quem recebe incidentes e quem toma ação?
- Qual janela assistida é aceitável?
- Como reportar problema sem expor segredo ou dado sensível?
- O cliente entende como pausar a POC se necessário?

### Próximo passo

- O cliente vê valor suficiente para continuar?
- O que precisa mudar antes de nova sessão?
- Quem aprova a próxima etapa?
- A decisão é Go, Pendente ou No-go?

## Critérios de sucesso da sessão

Marcar a sessão como bem-sucedida se:

- participantes entendem escopo beta assistido e fora de escopo;
- fluxo de incidente/evidência/auditoria foi compreendido;
- cliente consegue indicar se o processo tem aderência operacional;
- pendências técnicas, privacidade e operação foram registradas sem segredos;
- há decisão clara: Go, Pendente com responsável ou No-go.

## Critérios de pausa/no-go durante a sessão

Pausar se ocorrer:

- segredo, token, cookie, header ou URL assinada exposta;
- dado pessoal ou imagem identificável fora do aceite;
- tenant/organização incorreto;
- health/readiness quebrado sem mitigação aceita;
- evidência aparece sem clique explícito;
- cliente espera produção/SLA/automação crítica fora do escopo;
- falha técnica impede explicar o fluxo com honestidade.

## Registro final da sessão

Preencher após a reunião:

| Campo | Registro |
| --- | --- |
| Data | A preencher |
| Participantes internos | A preencher sem dados sensíveis |
| Participantes cliente | A preencher conforme política de privacidade |
| Ambiente usado | POC assistida / staging aprovado |
| Decisão | Go / Pendente / No-go |
| Principais achados | A preencher |
| Riscos | A preencher |
| Pendências técnicas | A preencher |
| Pendências privacidade/LGPD | A preencher |
| Próximo passo | A preencher |
| Responsável por follow-up | A preencher |

## Próximas ações típicas

- Se **Go**: agendar sessão controlada seguinte ou ampliar escopo com novo checklist.
- Se **Pendente**: criar cards com responsáveis e repetir readiness antes da próxima sessão.
- Se **No-go**: registrar causa, corrigir bloqueadores e não envolver cliente até nova decisão.

## Checklist rápido para o facilitador

- [ ] Não há credenciais no material aberto.
- [ ] Readiness foi revisado.
- [ ] O roteiro não promete produção/SLA.
- [ ] A demo usa tenant correto.
- [ ] Evidência só aparece sob ação explícita.
- [ ] Decisão final e responsáveis serão registrados.
