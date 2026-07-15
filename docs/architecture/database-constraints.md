# VigIA Safety — Restrições de banco e integridade

## Objetivo
Definir as restrições mínimas de integridade para identidade, organização e isolamento de tenant.

## Restrições em users
- `email_normalized` deve ter unicidade global.
- `email` deve ser obrigatório.
- `password_hash` deve ser obrigatório para contas com login.
- `status` deve ser um enum controlado.

## Restrições em organizations
- `name` obrigatório.
- `legal_name` obrigatório quando aplicável ao cadastro fiscal.
- `cnpj`/`tax_id` deve ser único quando informado.
- `status` deve ser um enum controlado.
- `created_by` deve referenciar um `user` válido.

## Restrições em organization_memberships
- unicidade composta: **(`organization_id`, `user_id`)**.
- `organization_id` e `user_id` obrigatórios.
- `role` e `status` obrigatórios.
- `invited_by` deve referenciar `user` quando houver convite.
- `joined_at` deve ser preenchido quando o status indicar vínculo ativo.

## Regra crítica: último org_owner
Não permitir remover, suspender ou deletar o último membro ativo com papel `org_owner` de uma organização.

Implementação esperada:
- antes de alterar memberships, validar a contagem de `org_owner` ativos;
- bloquear a operação quando restar apenas um `org_owner` ativo;
- exigir troca de ownership ou adição prévia de outro owner.

## Isolamento de dados operacionais
Toda tabela operacional deve possuir `organization_id`, por exemplo:
- sites
- cameras
- zones
- rules
- incidents
- evidence
- audit_logs
- notifications
- workers
- edge_workers

Restrições recomendadas:
- chave estrangeira para `organizations(id)`;
- índice por `organization_id`;
- validação de escopo em queries e mutations;
- bloqueio de FK cruzada entre tenants.

## Regras de exclusão
- preferir soft delete para entidades de identidade e organização;
- usar `deleted_at`/`removed_at` quando necessário;
- manter trilha de auditoria para mudanças sensíveis.
