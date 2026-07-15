# VigIA Safety — Modelo SaaS multi-tenant

## Objetivo
Especificar o modelo SaaS multi-tenant do **VigIA Safety** para o MVP, com foco em isolamento por organização, acesso por membership e integração com workers de borda.

## Decisões centrais
- **Organization** é o cliente/tenant principal.
- **User** é global e não pertence a uma única organização.
- O acesso do usuário às organizações ocorre por **OrganizationMembership**.
- Todos os dados de domínio pertencem a `organization_id`.
- **Edge workers** operam por organização/site e enviam eventos para a plataforma central.
- Instância dedicada / on-premise é caminho futuro de enterprise, **não** parte do MVP.

## Modelo de acesso
- `user`: identidade global autenticável.
- `organization`: unidade de negócio, contrato e isolamento.
- `organization_membership`: vínculo entre usuário e organização, com papel e status.
- O usuário pode ter múltiplas memberships em organizações diferentes.
- A autorização sempre combina identidade global + escopo da organização ativa.

## Propriedade dos dados
Todo dado operacional deve carregar `organization_id`, incluindo:
- sites
- câmeras
- zonas
- regras
- incidentes
- evidências
- auditoria
- configurações operacionais

Regra principal:
- nenhuma leitura ou escrita deve cruzar organizações sem autorização explícita de plataforma.

## Workers e borda
- Workers de borda são registros operacionais, não usuários com login no MVP.
- Cada worker pertence a uma organização e, normalmente, a um site.
- O worker captura/analisa localmente e envia eventos para a API central.
- A plataforma central valida, persiste e distribui os eventos.

## Diagrama textual do modelo SaaS
```text
                +-----------------------------+
                |    Plataforma SaaS central  |
                |  API + UI + eventos + audit|
                +--------------+--------------+
                               |
               autentica/autoriza por membership
                               |
      +------------------------+------------------------+
      |                                                 |
+-----+------+                                   +------+-----+
| Organization|                                   |  User      |
|  (tenant)   |<-- OrganizationMembership ------->|  global    |
+-----+------+                                   +------------+
      |
      | owns all domain data via organization_id
      v
  sites / cameras / zones / incidents / evidence / audit
      |
      | edge events
      v
 +-------------------+      send events      +-------------------+
 | Edge worker org/site| ------------------>  | API central SaaS  |
 +-------------------+                        +-------------------+
```

## Implicações práticas
- O tenant ativo deve estar explícito em sessão, cabeçalhos internos ou contexto de requisição.
- Consultas devem sempre filtrar por `organization_id`.
- Auditoria e evidências herdam o escopo da organização de origem.
- O onboarding deve criar a organização antes de vincular usuários.

## Fora do MVP
- Instância dedicada por cliente.
- Deploy on-premise completo para cada cliente.
- Isolamento físico como padrão do produto.
