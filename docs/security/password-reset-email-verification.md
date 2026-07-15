# Password reset and email verification

- Password reset requests always return a generic response to avoid email enumeration.
- Reset/verification tokens are high entropy, stored only as hashes, and are one-time use.
- Password reset tokens expire in a short window (target 15-60 minutes; this prototype uses 30 minutes).
- Password reset completion revokes existing sessions for the user.
- Email verification marks `email_verified_at` and cannot be reused.
- Email delivery is mocked via queued records; no SMTP/provider is used.
- Audit logs record request/completion events without exposing raw tokens.
- Apply rate limits at the API layer for request endpoints.
