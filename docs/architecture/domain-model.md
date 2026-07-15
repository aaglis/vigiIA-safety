# VigIA Safety — Modelo de domínio e entidades principais

## Escopo
Este documento descreve as entidades principais do domínio do **Intelliboard / VigIA Safety** para o MVP.

## Princípios
- SaaS centralizado multi-tenant.
- Toda entidade operacional pertence a uma organização via `organization_id`.
- `user` é global; acesso é concedido por `membership`.
- `worker` não é usuário de login no MVP; é um registro operacional. Ver [Users vs Workers](./users-vs-workers.md).
- O domínio deve ser compatível com LGPD: coletar apenas dados necessários para segurança.

## Entidades principais

### Organização
- Agrupa sites, pessoas, regras, ativos e eventos.
- Possui plano, status e configurações de compliance.

### Usuário
- Identidade global autenticável.
- Pode participar de uma ou mais organizações por meio de memberships.

### Membership
- Vínculo entre `user` e `organization`.
- Define papel organizacional: `org_owner`, `org_admin`, `manager`, `auditor`/`viewer` opcional.

### Site
- Unidade física monitorada (fábrica, planta, área, contrato).
- Pertence a uma organização.

### Department / Sector
- Estrutura interna do site para organizar áreas operacionais.
- Pode ser hierárquico, se necessário.

### Worker
- Pessoa operacional monitorada por segurança, sem login no MVP.
- Pode ser vinculada a um site, setor, turno, função e status de treinamento/EPI.

### Camera
- Equipamento de captura ligado a um site e, opcionalmente, a uma zona.
- Pode ser física ou lógica (ex.: stream consolidado).

### Zone
- Área de risco ou perímetro monitorado.
- Relaciona câmera(s), regras e eventos.

### Safety rule
- Regra de segurança aplicada em uma zona/site.
- Ex.: entrada sem capacete, acesso indevido, ausência de EPI obrigatório.

### Required PPE
- Conjunto de EPIs exigidos por zona, função ou regra.
- Ex.: capacete, óculos, luvas, colete.

### Edge worker
- Agente executado na borda para capturar/avaliar streams e emitir eventos.
- Pertence a uma organização e autentica com credencial técnica.

### Detection event
- Evento bruto ou semipronto emitido pelo edge worker.
- Pode originar um incidente candidato.

### Incident
- Registro de evento de segurança tratado pela operação.
- Mantém status de ciclo de vida, severidade, responsáveis e evidências.

### Evidence
- Snapshot, trecho de vídeo, metadados e trilha de acesso.
- Armazenada em storage privado e acessível apenas por permissão explícita.

### Notification
- Comunicação derivada de incidentes, regras ou escalonamentos.
- Ex.: e-mail, push, integração futura.

### Audit log
- Registro imutável de ações relevantes de segurança e administração.
- Inclui leitura de evidência, mudanças de status, permissões e configurações.

## Relações básicas
- `organization` 1:N `sites`
- `organization` 1:N `memberships`
- `user` 1:N `memberships`
- `site` 1:N `departments/sectors`
- `site` 1:N `workers`
- `site` 1:N `cameras`
- `site` 1:N `zones`
- `zone` 1:N `safety_rules`
- `zone` 1:N `required_ppe`
- `edge_worker` 1:N `detection_events`
- `detection_event` 0..1:N `incidents`
- `incident` 1:N `evidence`
- `incident` 0..N `notifications`
- qualquer ação relevante 1:N `audit_logs`

## Regras de tenant-safety
- Todas as tabelas operacionais devem carregar `organization_id`.
- Qualquer consulta deve ser filtrada por organização.
- Evidências e auditoria herdam o escopo da organização do incidente.

## Registro mínimo de worker sem violar LGPD
- Identificador interno do trabalhador.
- Organização, site e setor.
- Função operacional, turno e status ativo/inativo.
- Regras/EPIs aplicáveis.
- Incidentes associados ao trabalhador apenas quando necessários para segurança.
- Nunca armazenar produtividade, rastreamento contínuo ou reconhecimento facial como requisito do MVP.

## Não objetivos do MVP
- Login de trabalhador comum.
- Monitoramento de produtividade.
- Reconhecimento facial como base de identificação.
