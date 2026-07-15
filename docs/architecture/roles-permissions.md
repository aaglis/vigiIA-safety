# VigIA Safety — Papéis e matriz de permissões

## Princípios
- A autenticação é apenas para usuários humanos com `membership` em organização. Veja [Users vs Workers](./users-vs-workers.md).
- `worker` é entidade operacional do domínio; **não possui login no MVP**.
- A autorização deve ser mínima, explícita e auditável.
- Acesso da plataforma a dados de cliente é excepcional e sempre auditado.

## Papéis de plataforma

### platform_owner
- Controle total da plataforma.
- Pode criar/suspender organizações, gerir políticas globais e acessar auditoria da plataforma.

### platform_admin
- Administra a operação da plataforma.
- Pode criar/suspender organizações e apoiar suporte com acesso restrito.
- Acesso a evidências de clientes é **restrito, justificado e auditado**; não é acesso irrestrito por padrão.

### platform_support
- Suporte operacional com privilégios limitados.
- Pode diagnosticar problemas e consultar metadados mínimos necessários.
- Não possui acesso automático a evidências nem a configurações críticas.

## Papéis de organização

### org_owner
- Dono da organização.
- Pode administrar plano, membros, configurações críticas e segurança.

### org_admin
- Administra a organização no dia a dia.
- Pode gerenciar membros, sites, câmeras, zonas, regras e operação.

### manager
- Supervisiona a operação.
- Pode convidar/registrar workers e, se a política da organização permitir, criar usuários operacionais de baixa criticidade.
- Não pode criar `org_admin`, alterar `org_owner`, suspender a organização nem editar configurações críticas.

### auditor/viewer (opcional)
- Consulta dados, incidentes, evidências permitidas e trilhas de auditoria.
- Não altera configuração nem executa ações operacionais.

## Permissões canônicas
- `org.create`
- `org.suspend`
- `org.manage`
- `org.members.invite`
- `org.members.manage`
- `org.roles.manage`
- `org.security.manage`
- `sites.manage`
- `zones.manage`
- `cameras.manage`
- `workers.manage`
- `workers.register`
- `incidents.read`
- `incidents.write`
- `incidents.acknowledge`
- `incidents.resolve`
- `incidents.dismiss`
- `evidence.read`
- `audit.read`
- `edge.heartbeat.write`

## Matriz resumida

| Permissão | platform_owner | platform_admin | platform_support | org_owner | org_admin | manager | auditor/viewer |
|---|---:|---:|---:|---:|---:|---:|---:|
| org.create | sim | sim | não | não | não | não | não |
| org.suspend | sim | sim | não | não | não | não | não |
| org.manage | sim | sim | não | sim | sim | não | não |
| org.members.invite | sim | sim | não | sim | sim | sim | não |
| org.members.manage | sim | sim | não | sim | sim | não | não |
| org.roles.manage | sim | sim | não | sim | sim | não | não |
| org.security.manage | sim | sim | não | sim | sim | não | não |
| sites.manage | sim | sim | não | sim | sim | não | não |
| zones.manage | sim | sim | não | sim | sim | não | não |
| cameras.manage | sim | sim | não | sim | sim | não | não |
| workers.manage/register | sim | sim | não | sim | sim | sim | não |
| incidents.read | sim | sim | sim | sim | sim | sim | sim |
| incidents.write | sim | sim | não | sim | sim | sim | não |
| incidents.acknowledge/resolve/dismiss | sim | sim | não | sim | sim | sim | não |
| evidence.read | sim* | sim* | restrito** | sim | sim | sim | sim |
| audit.read | sim | sim | sim | sim | sim | não | sim |
| edge.heartbeat.write | sim | sim | não | sim | sim | não | não |

\* Acesso de plataforma a evidências exige justificativa, escopo mínimo e trilha de auditoria.

\** `platform_support` só acessa evidências quando explicitamente autorizado para suporte e com registro de auditoria.

## Regras de negócio
- `manager` pode convidar/registrar workers e usuários operacionais permitidos pela política, mas não cria administradores.
- Trocas de `org_owner` exigem fluxo específico e validação por `org_owner` ou `platform_owner`.
- A suspensão de organização é prerrogativa de plataforma (`platform_owner`/`platform_admin`) ou fluxo de compliance definido em contrato separado.
- O termo `worker` nunca deve ser tratado como role de login no MVP.
