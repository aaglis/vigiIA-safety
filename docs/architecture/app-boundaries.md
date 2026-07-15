# Fronteiras entre apps

## Princípio
Código entre apps não é compartilhado por import. O compartilhamento permitido é apenas por contratos versionados.

## Web
- Consome a API via HTTP.
- Usa OpenAPI e contratos para tipagem futura.
- Não deve importar lógica de backend nem do edge worker.

## API
- Expõe `/api/v1`.
- Valida permissões, tenant e auditoria.
- Não importa frontend.
- Não importa implementação do edge worker.

## Edge worker
- Usa credencial técnica própria.
- Publica eventos e heartbeats via HTTP.
- Consome contratos de evento e políticas.
- Não importa código da API.

## Compartilhamento permitido
- `packages/contracts/openapi`.
- Schemas JSON de eventos.
- `packages/contracts/permissions/permissions.yaml`.

## Proibições
- Import direto entre apps.
- Reuso de serviços internos por caminho de filesystem.
- Acoplamento implícito por código duplicado copiado entre apps.

## Estratégia de manutenção
Se houver necessidade de reaproveitar regra comum, a regra deve virar:
1. contrato;
2. schema;
3. documentação;
4. ou código utilitário isolado em pacote próprio futuro.
