# VigIA Safety — Política de RBAC

## Objetivo
Definir a política de controle de acesso baseada em papéis para plataforma e organizações.

## Escopo
- Inclui papéis de plataforma, papéis de organização e permissões canônicas.
- Aplica-se a usuários humanos autenticados e a entidades operacionais do domínio.

## Conceitos
- **Usuário humano**: acessa o sistema via `membership` em organização.
- **Worker**: entidade operacional sem login no MVP. Veja [Users vs Workers](../architecture/users-vs-workers.md).
- **Permissão**: ação atômica autorizável.
- **Papel**: conjunto de permissões atribuídas a um contexto.

## Papéis de plataforma
- `platform_owner`: administração total, incluindo criação e suspensão de organizações.
- `platform_admin`: operação ampla da plataforma, com acesso excepcional a evidências apenas com justificativa e auditoria.
- `platform_support`: suporte restrito, sem acesso irrestrito a dados sensíveis.

## Papéis de organização
- `org_owner`: dono do tenant, com controle máximo da organização.
- `org_admin`: administra membros, ativos operacionais e configuração não restrita.
- `manager`: operação diária e gestão de workers e incidentes; não altera estrutura crítica.
- `auditor/viewer` (opcional): leitura e auditoria sem mutação.

## Regras obrigatórias
1. `worker` não é papel de login no MVP.
2. `manager` pode convidar/registrar workers e usuários operacionais permitidos pela política.
3. `manager` não pode criar `org_admin`, trocar `org_owner`, suspender organização ou editar configurações críticas.
4. `platform_support` não recebe acesso automático a evidências.
5. Todo acesso de plataforma a evidências deve ser registrado com motivo, escopo e prazo.
6. Toda mudança de papel sensível deve gerar trilha de auditoria.
7. Em rotas protegidas, `actor` vem sempre da sessão/token do usuário autenticado; body/query nunca é fonte confiável.

## Matriz de alto nível

| Ação | platform_owner | platform_admin | platform_support | org_owner | org_admin | manager | auditor/viewer |
|---|---|---|---|---|---|---|---|
| Criar organização | sim | sim | não | não | não | não | não |
| Suspender organização | sim | sim | não | não | não | não | não |
| Convidar usuários | sim | sim | não | sim | sim | sim | não |
| Alterar papéis | sim | sim | não | sim* | sim | não | não |
| Gerir sites/câmeras/zonas | sim | sim | não | sim | sim | não | não |
| Gerir workers | sim | sim | não | sim | sim | sim | não |
| Ver incidentes | sim | sim | sim | sim | sim | sim | sim |
| Resolver incidentes | sim | sim | não | sim | sim | sim | não |
| Ver evidências | sim** | sim** | restrito** | sim | sim | sim | sim |
| Ver logs de auditoria | sim | sim | sim | sim | sim | não | sim |

\* Trocas de `org_owner` devem seguir fluxo controlado.

\** Acesso auditado e mínimo necessário.

## Critérios de auditoria
- registrar quem acessou, quando, por quê e quais objetos foram consultados;
- registrar concessões temporárias de suporte;
- registrar mudanças de papel e de escopo organizacional;
- registrar ações de suspensão, restauração e exclusão lógica de acesso.
