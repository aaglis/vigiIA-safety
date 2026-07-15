# PDC Compose

## Objetivo

Subir a stack PDC com frontend público na porta 80, API interna e proxy `/api/` para o backend, usando configuração de produção e endpoint S3 interno `http://minio:9000`.

## Arquivo

- [`infra/pdc/docker-compose.yml`](../../infra/pdc/docker-compose.yml)
- [`apps/web/nginx.conf`](../../apps/web/nginx.conf)

## Variáveis esperadas

- `JWT_SECRET`
- `REFRESH_TOKEN_SECRET`
- `METRICS_TOKEN`
- `DATABASE_URL` (opcional; padrão Postgres do compose)
- `REDIS_URL` (opcional; padrão Redis do compose)
- `ALLOWED_ORIGINS` (JSON array contendo a URL pública do PDC, por exemplo `[
  "https://pdc.example.com"
]`)
- `ALLOW_INTERNAL_S3_ENDPOINT=true`
- `S3_ENDPOINT_URL=http://minio:9000`
- `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` ou `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY`
- `EVIDENCE_BUCKET_NAME`

## Uso

`web` é o serviço público e escuta na porta 80; `api`, `postgres`, `redis`, `minio` e `minio-init` ficam internos.

```bash
docker compose -f infra/pdc/docker-compose.yml up --build
```

O bucket de evidências é criado automaticamente e permanece privado.
