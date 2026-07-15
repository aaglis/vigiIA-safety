# Separação de ambientes

## Política
Dev, staging e prod devem ser tratados como ambientes distintos, com segredos distintos e controles distintos.

## Regras
- não reutilizar JWT secrets entre ambientes;
- não reutilizar credenciais de banco, cache, MinIO/S3 ou SMTP entre ambientes;
- não reaproveitar API keys/edge-worker credentials entre ambientes;
- não apontar staging para buckets/filas de prod;
- não usar credenciais de produção em compose local.

## Dev
- pode usar mocks e credenciais `dev-only`;
- foco em facilitar execução local;
- nunca promover valores de dev para staging/prod.

## Staging
- espelha a topologia da produção com segredos próprios;
- valida rotação, revogação e auditoria;
- serve como último ambiente de verificação funcional.
- usa backends reais: `REPOSITORY_BACKEND=postgres` e rate limit compartilhado via Redis;
- não aceita valores dev-only, placeholders ou credenciais reutilizadas de local/prod;
- segue o runbook `docs/deployment/staging-pilot.md` para smoke pós-deploy, rollback e leitura de logs.

## Prod
- usa secret manager;
- rotação controlada;
- auditoria obrigatória;
- acesso mínimo e segregado.
