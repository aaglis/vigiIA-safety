# Auth session strategy

- Access token: short-lived JWT in HttpOnly cookie.
- Refresh token: opaque token, rotated on every refresh, stored hashed server-side.
- Sessions: revocable in-memory for now; ready to move to DB later.
- Passwords: PBKDF2-HMAC stdlib fallback for prototype.
- Production target: Argon2id once dependency is available.
- Cookies: access/refresh em cookies HttpOnly; Secure configurável por ambiente; SameSite=Lax por padrão; refresh cookie restrito ao path `/api/v1/auth/refresh`.
- CSRF: cookie legível `csrf_token` emitido no login/refresh/logout; mutações browser enviam `X-CSRF-Token` com o mesmo valor. Refresh, logout, incident actions e evidence mutations validam CSRF e Origin/Referer.
- `GET /api/v1/auth/me` returns user, memberships, and active-org permissions.

Veja também [secret management policy](./secret-management-policy.md) e [environment separation](./environment-separation.md).

Em produção, `JWT_SECRET` e `REFRESH_TOKEN_SECRET` vêm do ambiente/secret manager.
