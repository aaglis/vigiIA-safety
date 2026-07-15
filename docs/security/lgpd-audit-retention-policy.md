# Política unificada de LGPD, auditoria e retenção

## Objetivo e escopo do MVP
VigIA Safety é uma solução de segurança do trabalho e conformidade operacional. O foco é prevenção de incidentes, registro de evidências e trilha auditável. Não é uma ferramenta de produtividade.

No MVP:
- não usar reconhecimento facial;
- não armazenar vídeo contínuo por padrão;
- coletar somente o necessário para evento, incidente, auditoria e operação.

## Dados coletados e finalidade
Podem ser coletados:
- dados de organização, site, câmera e worker;
- metadados de eventos/incidentes;
- snapshots/clipes curtos apenas quando houver gatilho;
- logs de auditoria e eventos administrativos;
- informações mínimas para autenticação, convites e recuperação de conta.

Finalidade:
- segurança do trabalho;
- investigação de incidentes;
- conformidade operacional;
- auditoria de acesso e ações administrativas.

## Minimização e limites no MVP
Proibido por padrão no MVP:
- reconhecimento facial;
- gravação contínua sem evento;
- uso para monitoramento de produtividade;
- retenção de dados além do necessário sem política contratada.

## Retenção padrão
Os prazos abaixo são padrão de produto e podem ser ajustados por contrato/tenant:

| Tipo de dado | Retenção padrão |
| --- | --- |
| Metadados de incidentes/eventos | 180 dias |
| Snapshots | 30 dias |
| Clipes curtos | 30 dias |
| Audit logs | 365 dias |
| Convites | 30 dias após expiração/uso |
| Password reset tokens | 24 horas |
| Sessões/tokens de refresh | até revogação + 30 dias |

## Quem pode ver evidências e histórico por worker
Regra geral:
- usuários com escopo operacional da mesma organização podem ver metadados;
- evidências (imagens/clipes) exigem permissão específica;
- histórico por worker deve ser filtrado por `organization_id` e contexto do site.

Matriz resumida:
- **Org owner / org admin**: podem ver metadados e evidências da própria organização, com auditoria.
- **Manager / auditor viewer**: podem ver metadados; evidências apenas se a política contratada permitir.
- **Worker comum / sem permissão**: não vê evidências nem histórico ampliado.
- **Platform admin/support**: acesso apenas quando necessário para operação da plataforma e sempre auditado.

## Eventos obrigatórios de auditoria
Registrar sempre:
- visualização de evidência;
- download/compartilhamento de evidência;
- alteração de papéis/permissões;
- convites criados, aceitos, revogados e expirados;
- resets de senha e verificações de e-mail;
- criação/edição/resolução de incidentes;
- alteração de configurações de retenção, organização, sites e regras;
- tentativa negada de acesso a dados sensíveis.

## Exportação, exclusão e anonimização futuras
Quando solicitado em contrato ou por obrigação legal, a plataforma deve suportar:
- exportação dos dados do tenant;
- exclusão segura de dados expirados ou solicitados;
- anonimização/pseudonimização quando exclusão total não for possível;
- trilha auditável de quem executou a ação e quando.

## Responsabilidades
### Cliente/controlador
- definir configurações contratuais de retenção;
- indicar quem pode acessar evidências;
- solicitar exportação/exclusão quando aplicável.

### Plataforma/operador
- aplicar minimização e isolamento por organização;
- registrar auditoria obrigatória;
- manter retenção e expurgo conforme política;
- bloquear acesso sem permissão ou contexto adequado.
