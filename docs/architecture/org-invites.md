# Organization invites

- Invites are one-time tokens, hashed at rest, expiring after ~7 days.
- Statuses: `pending`, `accepted`, `expired`, `revoked`.
- Email delivery is mocked via queued records; no SMTP/provider is used.
- Org owners/admins can invite org admins/managers/auditor-viewers.
- Managers are conservative in MVP: they can only invite `auditor_viewer`.
- Workers are not invited as login users in this MVP; worker registration is a separate domain.
- Accepting an invite can create a user or link an existing user by email and activates the membership.
- Audit logs are recorded for create, resend, revoke, and accept.
