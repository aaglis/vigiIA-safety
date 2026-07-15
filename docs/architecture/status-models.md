# VigIA Safety — Modelos de status

## Objetivo
Padronizar os status das entidades de identidade, organização e memberships.

## Status de users
- `active`
- `suspended`
- `deleted`

Uso:
- `active`: conta disponível para login;
- `suspended`: acesso bloqueado temporariamente;
- `deleted`: conta removida logicamente.

## Status de organizations
- `active`
- `invited` (quando aplicável ao onboarding/contrato)
- `suspended`
- `deleted`

Uso:
- `active`: organização operando normalmente;
- `suspended`: acesso restringido por compliance, contrato ou decisão administrativa;
- `deleted`: desativação lógica/encerramento.

## Status de organization_memberships
- `invited`
- `active`
- `suspended`
- `removed`

Uso:
- `invited`: convite enviado e ainda não aceito;
- `active`: vínculo válido com acesso;
- `suspended`: vínculo temporariamente bloqueado;
- `removed`: vínculo encerrado sem apagar histórico.

## Status de platform roles
Platform roles não dependem de fluxo de convite e podem ser representados por:
- `active`
- `suspended`

## Status de workers
Workers são registros operacionais, não contas de login no MVP.

Status sugeridos:
- `active`
- `inactive`
- `retired`

## Regras gerais
- status devem ser enums/documentados, nunca strings livres;
- mudanças de status devem ser auditáveis;
- exclusão lógica é preferível para preservar histórico.
