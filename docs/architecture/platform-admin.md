# Platform admin

- Platform admins manage organizations and first owner assignment.
- Endpoints:
  - `POST /api/v1/platform/organizations`
  - `GET /api/v1/platform/organizations`
  - `POST /api/v1/platform/organizations/{organization_id}/suspend`
  - `POST /api/v1/platform/organizations/{organization_id}/reactivate`
  - `GET /api/v1/platform/audit-logs`
- Permission gate: platform owner/admin only.
- Every mutation writes a platform audit log.
- Evidence access is intentionally not implemented here; break-glass access remains a future restricted/audited card.
- Invite/email flow is placeholder-only for MVP; a dedicated invite card should replace it later.
