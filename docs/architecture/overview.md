# VigIA Safety — Visão geral da arquitetura inicial

## Objetivo
Definir a arquitetura inicial do **VigIA Safety**, uma plataforma SaaS multitenant para segurança industrial com visão computacional, evidência auditável e operação híbrida entre nuvem e borda.

Detalhes de organização do monorepo: [monorepo structure](./monorepo-structure.md) e [app boundaries](./app-boundaries.md).

## Decisões-base
- **Produto:** VigIA Safety
- **Modelo:** SaaS centralizado multi-tenant + workers de CV em edge/on-premise
- **Separação obrigatória:** frontend, API, worker de visão computacional e worker de notificação/processamento de eventos
- **Persistência:** todas as tabelas operacionais possuem `organization_id`

## Stack oficial inicial

### Frontend
- `apps/web`
- React
- Vite
- TypeScript
- Tailwind CSS

### Backend/API
- `apps/api`
- FastAPI
- Pydantic
- SQLAlchemy + Alembic
- PostgreSQL
- Redis
- MinIO/S3 para evidências

### Edge/CV
- `apps/edge-worker`
- Python
- OpenCV
- YOLO (fase futura)

### Processamento assíncrono
- Worker de eventos/notificações separado da API
- Redis como base para filas, jobs e coordenação inicial

## Responsabilidades por componente

### Frontend
- Login e sessão do usuário
- Dashboard por organização
- Gestão de câmeras, setores, regras, incidentes e auditoria
- Visualização de evidências com URLs assinadas

### API
- Autenticação, autorização e RBAC por tenant
- Cadastro e configuração da organização
- Recebimento de eventos de detecção
- Validação de eventos vindos do edge
- Criação de incidentes, workflows e trilhas de auditoria
- Emissão de URLs assinadas para evidências

### Edge worker
- Captura de stream local
- Inferência de CV
- Geração de eventos de detecção
- Operação próxima à câmera para reduzir latência e tráfego de vídeo

### Worker de notificação/eventos
- Processamento assíncrono de eventos aceitos pela API
- Notificações por e-mail/WhatsApp/push no futuro
- Regras de escalonamento e reprocessamento

## Segurança e isolamento
- Senhas com **Argon2id**
- Access token curto em cookie **HttpOnly** e **Secure**
- Refresh token opaco e rotativo
- Proteção CSRF
- RBAC com escopo de tenant
- Evidências em bucket privado com acesso por URL assinada e auditoria

## Princípios da arquitetura
- Vídeo bruto não deve trafegar para a nuvem por padrão
- O backend é a fonte de verdade para incidentes e workflows
- O worker de CV detecta; a API valida e decide
- O sistema deve permitir operação on-premise, cloud-first e híbrida
