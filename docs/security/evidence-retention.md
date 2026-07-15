# Política de retenção de evidências

## Objetivo
Definir retenção configurável por organização para metadados, snapshots e clipes de evidência.

Política consolidada: [LGPD, auditoria e retenção](./lgpd-audit-retention-policy.md).

## Regras
- Cada organização define sua retenção padrão.
- O sistema deve suportar políticas diferentes por tenant.
- Metadados e evidências podem ter prazos distintos.
- Expiração automática deve remover ou anonimizar conforme a política.

## Escopo de retenção
- **Metadados de evento**: mantidos pelo prazo configurado pela organização.
- **Snapshots e clipes**: mantidos apenas pelo prazo necessário para investigação, auditoria e cumprimento legal.
- **Snapshots binários do edge**: seguem a mesma política de snapshot e devem ser armazenados em bucket privado, com URL assinada apenas sob demanda.
- **Vídeo contínuo**: não armazenado por padrão.

## Diretrizes operacionais
- Preferir retenção curta por padrão.
- Permitir extensão manual somente com justificativa.
- Registrar quando uma evidência entra em retenção excepcional.
- Garantir exclusão segura ao final do prazo.

## Procedimento operacional
1. Executar `purge-preview` por organização para listar apenas itens elegíveis.
2. Revisar a lista e a justificativa antes de remover qualquer item.
3. Executar `purge` somente com confirmação explícita.
4. Registrar o motivo do expurgo e o responsável.
5. Auditoria mínima deve incluir `evidence.upload_url`, `evidence.download`, `retention.update`, `purge.dry_run` e `purge.confirm`.

## Implementação esperada
- Configuração por `organization_id`.
- Jobs de expurgo periódicos.
- Política explícita para objetos em MinIO/S3 privado.
- Trilhas de auditoria para exclusão e retenção estendida.
- Exportação futura deve seguir o mesmo escopo por `organization_id` e não deve misturar tenants.

## Checklist de URL assinada e logs
- URLs assinadas de download só devem ser geradas após ação explícita do usuário no dashboard.
- A UI não deve renderizar URL assinada, assinatura ou query string antes do clique em “Abrir evidência segura”.
- Logs e auditoria podem registrar `organization_id`, `incident_id`, `file_id`, `object_key`, mídia e ação, mas não devem registrar `download_url`, `upload_url`, assinatura, token, cookie ou headers de autenticação.
- Upload binário do edge worker deve usar apenas a URL assinada de storage, sem repassar `X-Edge-Api-Key`, `X-Edge-Client-Id` ou `X-Request-ID`.
- TTL de URL assinada deve ser curto e configurado por ambiente; staging/prod devem usar bucket privado e URLs sob demanda.
