# OpenAPI e contratos versionados

## Estratégia
O contrato HTTP oficial da plataforma fica versionado em `/api/v1`.

## Diretrizes
- O OpenAPI da API deve refletir a versão pública atual.
- Mudanças quebradoras exigem nova versão, não substituição silenciosa.
- O frontend consome a API por HTTP e se orienta pelo contrato.
- O edge worker também depende de contrato versionado, não de imports.

## Organização futura
- `packages/contracts` pode conter exportações geradas do OpenAPI.
- Schemas de eventos e permissões permanecem separados por tipo.
- A geração automática futura deve ser compatível com backwards compatibility.

## Compatibilidade
- manter campos opcionais quando possível;
- documentar depreciações;
- preferir adicionar novas rotas/versões em vez de alterar o contrato existente.
