# VigIA Safety — Esquema de identidade e organização

## Objetivo
Modelar as entidades centrais de identidade, organização e acesso do **VigIA Safety** no SaaS multi-tenant.

## Princípios
- **Organization** é o tenant/cliente principal.
- **User** é global e autenticável uma única vez.
- O acesso do usuário às organizações ocorre por **OrganizationMembership**.
- **Platform roles** são globais e separados de memberships de organização.
- Trabalhadores/operadores são entidades operacionais, **não** usuários no MVP. Veja também [Users vs Workers](./users-vs-workers.md).
- Toda tabela operacional deve possuir `organization_id`.

## Tabela users
Campos mínimos:
- `id`
- `email`
- `email_normalized`
- `password_hash`
- `full_name`
- `phone`
- `status`
- `email_verified_at`
- `last_login_at`
- `created_at`
- `updated_at`

Regras:
- `email_normalized` deve ser único.
- `password_hash` nunca é armazenado em texto puro.
- `status` representa a situação global da conta.

## Tabela platform_roles
Papéis globais da plataforma, separados de organizações.

Exemplos:
- `platform_owner`
- `platform_admin`
- `platform_support`

Uso:
- administram a plataforma central;
- não substituem membership organizacional;
- podem coexistir com memberships em organizações.

## Tabela organizations
Campos mínimos:
- `id`
- `name`
- `legal_name`
- `cnpj` / `tax_id`
- `status`
- `retention_policy_days`
- `retention_policy_kind`
- `created_by`
- `created_at`
- `updated_at`

Regras:
- `created_by` referencia o usuário que criou a organização.
- políticas de retenção podem variar por contrato/plano.
- `status` controla operação e acesso da tenant.

## Tabela organization_memberships
Campos mínimos:
- `id`
- `organization_id`
- `user_id`
- `role`
- `status`
- `invited_by`
- `joined_at`
- `created_at`
- `updated_at`

Regras:
- representa o vínculo de acesso do usuário à organização;
- o usuário pode ter múltiplas memberships em organizações diferentes;
- o papel é de organização, não global;
- `invited_by` registra quem convidou;
- `joined_at` registra quando o usuário aceitou/entrou.

## Diagrama textual
```text
User (global) ---< OrganizationMembership >--- Organization (tenant)
   |                                                 |
   +--- PlatformRole (global)                         +--- domain tables via organization_id
```
