# CSRF, CORS e rate limit

## Política
- CORS é restrito a `settings.allowed_origins`.
- Requests com cookie de autenticação devem validar `Origin`/`Referer` em métodos mutáveis.
- `POST/PUT/PATCH/DELETE` autenticados com cookie devem enviar `X-CSRF-Token` igual ao cookie `csrf_token`.
- `csrf_token` não é `HttpOnly` para permitir leitura pelo frontend.
- `access_token` e `refresh_token` permanecem `HttpOnly`.

## Fluxo
1. Login/refresh retornam cookies de auth e também um cookie CSRF.
2. O frontend copia o valor do cookie CSRF para `X-CSRF-Token` em mutações.
3. Logout e refresh ficam protegidos por CSRF + validação de origem.

## Rate limit
- Reutilize `security.rate_limit.rate_limit(...)` para:
  - login
  - refresh
  - password reset
  - invite / accept invite
  - endpoints sensíveis futuros
- O limitador usa backend configurável por `RATE_LIMIT_BACKEND=auto|memory|redis`.
- Em `APP_ENV=test`, o fallback in-memory mantém testes rápidos e isolados.
- Em Compose/dev profissional, staging e produção, use Redis compartilhado (`RATE_LIMIT_BACKEND=redis`) para contagem entre processos/containers.
- As chaves usam hash de IP/e-mail/user id para evitar vazamento de identificadores em Redis/logs.

## Respostas genéricas
- Login, reset e convite devem retornar mensagens genéricas para evitar enumeração.
- Ex.: `invalid credentials`, `if the account exists, an email will be sent`.

## Ambientes
- Local: `cookie_secure=false`, `cookie_samesite=lax`.
- Produção: `cookie_secure=true` e origens frontend explícitas.
