# Estrutura do monorepo e versionamento

## Objetivo
Definir a estrutura oficial do monorepo do VigIA Safety, suas fronteiras e o fluxo de dependências permitido.

## Estrutura principal
- `apps/web` — frontend React/Vite/TypeScript/Tailwind.
- `apps/api` — backend FastAPI.
- `apps/edge-worker` — worker Python de visão computacional.
- `packages/contracts` — contratos versionados compartilhados.
- `infra/compose` — ambiente local com Docker Compose.
- `docs/architecture` — decisões, modelo SaaS e fronteiras.
- `docs/security` — privacidade, auditoria, retenção e segurança.
- `docs/deployment` — deploy local e futuro.
- `docs/edge-worker` — comportamento e estratégia do worker.

## Responsabilidade por pasta
### apps/web
Interface do usuário, consumo de API por HTTP e contratos documentados.

### apps/api
Fonte de verdade da plataforma: autenticação, autorização, RBAC, incidentes, auditoria, evidências e integrações.

### apps/edge-worker
Processamento local na borda, detecção e envio de eventos para a API.

### packages/contracts
Contrato compartilhado, não implementação compartilhada.
- OpenAPI e decisões de API.
- Schemas JSON de eventos (`DetectionEvent v1`, `EdgeHeartbeat v1`, etc.).
- Permissões e políticas versionadas.

### infra/compose
Somente orquestração local, sem misturar regra de negócio.

## Fluxo de dependências permitido
- Web → API por HTTP.
- Edge worker → API por HTTP.
- Todos → `packages/contracts` para schemas e permissões.

## Regra de fronteira
É proibido importar código de implementação entre apps.
- `apps/web` não importa `apps/api` nem `apps/edge-worker`.
- `apps/api` não importa `apps/web` nem `apps/edge-worker`.
- `apps/edge-worker` não importa `apps/api` nem `apps/web`.

O compartilhamento acontece apenas por contratos, schemas e documentação em `packages/contracts`.

## Versionamento
- API exposta em `/api/v1`.
- Eventos com versão explícita no schema.
- `DetectionEvent v1` e `EdgeHeartbeat v1` são o ponto de partida.
- Mudanças quebradoras exigem nova versão, nunca substituição silenciosa.

## Estratégia futura de split
- `apps/edge-worker` deve poder virar repositório independente sem mudança de contrato.
- O worker mantém apenas integração HTTP + contratos.
- Qualquer lógica compartilhada deve ser movida para contratos ou especificação, não para imports diretos.
