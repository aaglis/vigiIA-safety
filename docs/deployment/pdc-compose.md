# PDC Compose

## Objetivo

Subir a API com Postgres, Redis e MinIO locais para PDC, usando configuração de produção e endpoint S3 interno `http://minio:9000`.

## Arquivo

- [`infra/pdc/docker-compose.yml`](../../infra/pdc/docker-compose.yml)

## Variáveis esperadas

- `JWT_SECRET`
- `REFRESH_TOKEN_SECRET`
- `METRICS_TOKEN`
- `DATABASE_URL` (opcional; padrão Postgres do compose)
- `REDIS_URL` (opcional; padrão Redis do compose)
- `ALLOWED_ORIGINS` (opcional)
- `ALLOW_INTERNAL_S3_ENDPOINT=true`
- `S3_ENDPOINT_URL=http://minio:9000`
- `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` ou `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY`
- `EVIDENCE_BUCKET_NAME`

## Uso

```bash
docker compose -f infra/pdc/docker-compose.yml up --build
```

O bucket de evidências é criado automaticamente e permanece privado.
