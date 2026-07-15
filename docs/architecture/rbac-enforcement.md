# RBAC enforcement

- Use `security/permissions.py` as the canonical role -> permission map.
- Use `security/dependencies.py` for FastAPI authorization dependencies.
- Route pattern for tenant-scoped resources:
  - `get_current_user` -> `get_current_organization_membership(org_id)` -> `require_permission("...")`
- Incident read routes require `incidents.read`.
- Incident mutation routes require the matching incident permission.
- Platform org management uses platform-role checks.
- `manager` cannot suspend organizations, change org owners, or mutate critical org settings.
- Evidence access remains separate; break-glass access is future work and must be audited.
