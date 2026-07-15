# VigIA Safety — Isolamento de tenant

## Objetivo
Definir as regras de isolamento entre tenants para o **VigIA Safety** no modelo SaaS multi-tenant.

## Princípios
- `organization` é o limite lógico de isolamento.
- `user` é global, mas só acessa organizações via membership.
- Todo objeto operacional pertence a uma organização.
- O código deve tratar o tenant como contexto obrigatório, nunca opcional.

## Regras de isolamento
1. Toda tabela de domínio deve possuir `organization_id`.
2. Toda query deve ser filtrada por `organization_id`.
3. Toda mutation deve validar o tenant ativo.
4. URLs, filtros e páginas nunca devem expor dados de outra organização.
5. Evidências e logs de auditoria seguem o mesmo isolamento do incidente.

## Modelo recomendado de autorização
- Autenticação identifica o `user` global.
- A autorização resolve a `organization` ativa.
- A permissão final é calculada por `OrganizationMembership.role`.
- O backend deve rejeitar acesso quando a membership não existir ou estiver inativa.

## Dados que precisam de tenant explícito
- cadastros operacionais
- regras e configurações
- incidentes e investigações
- evidências e anexos
- trilhas de auditoria
- eventos processados vindos do edge

## Edge workers e isolamento
- Cada edge worker pertence a uma organização e a um site.
- O worker usa credencial técnica própria.
- O worker só pode enviar eventos do seu tenant.
- A API central associa o evento ao `organization_id` antes de persistir.

## Controles mínimos de segurança
- Escopo de organização em todas as consultas.
- Chaves/credenciais técnicas separadas por organização.
- Auditoria de leitura de evidências.
- Bloqueio de acesso cruzado por UUID/ID adivinhado.

## Exemplo de fluxo seguro
1. Usuário autentica globalmente.
2. Sistema carrega memberships disponíveis.
3. Usuário escolhe uma organização ativa.
4. Requisições passam a usar `organization_id` daquele contexto.
5. API e UI exibem somente dados daquele tenant.

## Não objetivos do MVP
- Bancos de dados separados por tenant.
- Schema por tenant como requisito padrão.
- Instalação dedicada como oferta inicial.
