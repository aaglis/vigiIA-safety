# VigIA Safety — Briefing para design inicial

## 1. O que é o projeto

**VigIA Safety** é uma plataforma SaaS multi-tenant para segurança do trabalho em ambientes industriais. O produto usa eventos de visão computacional enviados por edge workers para identificar situações de risco, registrar incidentes, preservar evidências e apoiar equipes de segurança, supervisores e gestores na resposta operacional.

O foco do MVP é provar o fluxo:

> câmera/vídeo → edge worker → evento de detecção → incidente → dashboard → reconhecimento/resolução → auditoria/evidência

O produto deve ser percebido como uma ferramenta de **segurança e conformidade**, não como vigilância de produtividade.

## 2. Proposta de valor

- Reduzir tempo de resposta a incidentes de segurança.
- Ajudar empresas a identificar riscos recorrentes em áreas industriais.
- Gerar histórico auditável de incidentes, evidências e ações tomadas.
- Apoiar conformidade interna, segurança do trabalho e governança operacional.
- Preservar privacidade: sem reconhecimento facial no MVP e sem vídeo contínuo por padrão.

## 3. Público-alvo

### Clientes

- Indústrias, fábricas, centros logísticos, obras, mineração, energia, metalurgia e operações com zonas de risco.
- Empresas com equipes de SESMT, segurança do trabalho, operação industrial e compliance.

### Usuários do sistema

- **Platform owner/admin**: administra a plataforma SaaS.
- **Org owner/admin**: administra a organização cliente.
- **Manager/supervisor**: acompanha incidentes, trabalhadores, câmeras e áreas.
- **Auditor/viewer**: consulta evidências, histórico e auditoria conforme permissão.

### Importante

Funcionários monitorados são modelados como **Workers**, não como usuários logados no MVP. Eles não têm senha, sessão ou portal próprio nesta fase.

## 4. Funcionalidades planejadas/atuais do MVP

### Plataforma e autenticação

- SaaS multi-tenant com organizações isoladas.
- Usuários globais com memberships por organização.
- RBAC por papéis e permissões.
- Autenticação com sessão/cookies, refresh token rotacionável e proteção CSRF/origin.
- Configuração e segredos centralizados por ambiente.

### Domínio operacional

- Sites/unidades por organização.
- Setores/departamentos.
- Workers/funcionários monitorados.
- Câmeras.
- Zonas de risco.
- Regras de segurança e EPIs obrigatórios.
- Incidentes com status, severidade, confiança, timestamps e auditoria.

### Edge workers

- Worker técnico por organização/site.
- Autenticação por `client_id` + API key hash-only.
- Heartbeat.
- Envio de eventos de detecção.
- Escopo por organização, site e câmeras permitidas.
- Revogação de credenciais.

### Incidentes e evidências

- Criação de incidente a partir de evento de detecção.
- Dashboard/listagem de incidentes como fluxo central do produto.
- Reconhecer, resolver ou descartar incidente.
- Evidências privadas associadas ao incidente.
- Modelo compatível com MinIO/S3 usando chaves tenant-safe.
- URLs assinadas curtas e auditoria de acesso.

### Segurança, LGPD e auditoria

- Finalidade declarada: segurança do trabalho e conformidade.
- Sem reconhecimento facial no MVP.
- Sem vídeo contínuo por padrão.
- Armazenamento mínimo: eventos, metadados e evidências curtas quando necessário.
- Audit log para ações sensíveis.
- Retenção por organização.
- Segredos reais nunca em Git, chat, issue, card ou README.

## 5. Estado atual do projeto

O projeto já possui uma base técnica e documental robusta:

- Monorepo com `apps/web`, `apps/api`, `apps/edge-worker`, `packages/contracts`, `infra/compose` e `docs`.
- API FastAPI em estrutura inicial.
- Frontend React/Vite/TypeScript/Tailwind em scaffold.
- Edge worker Python em skeleton/mock.
- Contratos versionados para eventos.
- Docker Compose local planejado.
- Documentação de arquitetura, segurança, LGPD, RBAC, monorepo e deploy local.
- Testes unitários para vários fluxos de domínio.

Ainda não é um produto final. O estado atual é uma fundação de MVP, com várias partes em memória/mock, usada para validar arquitetura e fluxo antes de implementar persistência real, dashboard conectado e storage real.

## 6. Promessa principal para comunicar na landing page

**VigIA Safety ajuda equipes industriais a transformar detecções de risco em incidentes auditáveis e acionáveis, com privacidade, rastreabilidade e isolamento por cliente.**

Mensagens sugeridas:

- “Segurança industrial assistida por visão computacional.”
- “Detecte riscos, registre incidentes e acompanhe a resposta operacional.”
- “Evidências privadas, auditoria completa e controle por organização.”
- “Construído para segurança do trabalho — não para vigilância de produtividade.”

## 7. Tom de comunicação

O tom deve ser:

- Confiável.
- Técnico sem ser frio.
- Seguro e institucional.
- Moderno, mas não “hype”.
- Focado em operação real, conformidade e redução de risco.

Evitar:

- Linguagem de vigilância ou controle de produtividade.
- Promessas absolutas como “elimina todos os acidentes”.
- Exageros sobre IA autônoma.
- Cenas que pareçam policiamento de funcionários.

## 8. Conceitos visuais desejados

### Identidade

- Industrial moderno.
- Segurança operacional.
- Tecnologia confiável.
- Monitoramento responsável.
- Precisão, rastreabilidade e proteção.

### Cores sugeridas

Direções possíveis:

- Azul escuro / navy: confiança, tecnologia e segurança.
- Ciano ou azul elétrico: visão computacional, detecção, dados.
- Verde: status seguro/resolvido/conformidade.
- Âmbar/laranja: alerta/incidente/atenção.
- Cinzas neutros: ambiente industrial, dashboards, seriedade.

Evitar uma paleta muito agressiva em vermelho/preto, para não parecer produto de vigilância ou emergência permanente.

### Visualizações úteis

- Cards de incidentes.
- Linha do tempo do incidente.
- Status de workers/câmeras.
- Mapa/lista de sites.
- Indicadores: incidentes abertos, tempo até reconhecimento, workers online, evidências auditadas.
- Mock de câmera com zonas marcadas, sem expor rosto ou pessoa identificável.

## 9. Landing page — conteúdo sugerido

### Hero

Título possível:

> Segurança industrial assistida por visão computacional

Subtítulo possível:

> Detecte eventos de risco, registre incidentes e acompanhe respostas com evidências privadas, auditoria e isolamento por organização.

CTA principal:

- “Solicitar demonstração”
- “Conhecer o MVP”

CTA secundário:

- “Ver como funciona”

### Seções recomendadas

1. **Como funciona**
   - Edge worker monitora câmera/vídeo.
   - Evento de risco é enviado para a API.
   - Incidente aparece no dashboard.
   - Supervisor reconhece/responde.
   - Evidência e auditoria ficam registradas.

2. **Casos de uso iniciais**
   - Zonas de risco.
   - Uso de EPI, como capacete/colete.
   - Incidentes por site/câmera/setor.
   - Histórico auditável.

3. **Segurança e privacidade desde o início**
   - Sem reconhecimento facial no MVP.
   - Sem vídeo contínuo por padrão.
   - Evidências privadas.
   - Retenção configurável.
   - Audit log.

4. **Feito para operação multi-tenant**
   - Organizações isoladas.
   - Papéis e permissões.
   - Edge workers por site.
   - Contratos versionados.

5. **Dashboard operacional**
   - Incidentes abertos.
   - Status de câmeras/workers.
   - Evidências.
   - Auditoria.

## 10. Página de login — direção

Objetivo: transmitir segurança, clareza e ambiente corporativo.

Elementos sugeridos:

- Logo VigIA Safety.
- Campo e-mail.
- Campo senha.
- CTA “Entrar”.
- Link “Esqueci minha senha”.
- Mensagem curta: “Acesso restrito a usuários autorizados.”
- Nota discreta: “Protegido por sessão segura e auditoria de acesso.”

Evitar:

- Login social no MVP.
- Visual lúdico demais.
- Promessas de IA exageradas.

## 11. Diferenciais a comunicar com cuidado

- Multi-tenant desde o início.
- Edge workers com credencial técnica própria.
- Evidências isoladas por organização.
- Audit log para ações sensíveis.
- Políticas de LGPD, retenção e segredos documentadas desde a fundação.
- Arquitetura modular: web, API, edge worker, contratos e infraestrutura separados.

## 12. Funcionalidades fora do escopo inicial

Não posicionar como disponível agora:

- Reconhecimento facial.
- Streaming ao vivo contínuo.
- WhatsApp real.
- App mobile.
- Portal do trabalhador.
- Analytics avançado/BI.
- Billing.
- On-prem completo.
- Treinamento real de modelo CV.

Esses itens podem aparecer como visão futura apenas se necessário, sem destaque na landing inicial.

## 13. Sugestão de estrutura de navegação

- Produto
- Como funciona
- Segurança e LGPD
- Arquitetura
- Solicitar demonstração
- Entrar

## 14. Frase de posicionamento final

> O VigIA Safety transforma eventos de risco em incidentes rastreáveis, com evidências privadas, auditoria e governança multi-tenant para operações industriais.
