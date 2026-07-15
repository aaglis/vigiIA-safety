# Checklist de segredos por ambiente

## Dev
- [ ] `.env` real não foi commitado.
- [ ] valores `dev-only` estão limitados ao ambiente local.
- [ ] credenciais de exemplo não são usadas em produção.

## Staging
- [ ] segredos próprios do ambiente foram configurados.
- [ ] nenhum segredo de dev foi reaproveitado.
- [ ] rotação foi testada antes do deploy.
- [ ] logs não expõem segredos.

## Prod
- [ ] secret manager configurado.
- [ ] `.env` com segredo real não é usado como fonte principal.
- [ ] JWT/session secrets e chaves técnicas estão separados por ambiente.
- [ ] MinIO/S3, SMTP e API keys foram validados.
- [ ] edge-worker credentials podem ser revogadas e reemitidas.
- [ ] auditoria de rotação/revogação está ativa.

## Antes de publicar
- [ ] confirmar que cards/issues/README não contêm segredos.
- [ ] confirmar que nenhum arquivo versionado contém credenciais reais.
- [ ] confirmar que staging e prod não compartilham segredo.
