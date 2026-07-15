# Tenant Isolation Threat Model

Este documento consolida o modelo de ameaças transversal do VigIA Safety para
operações multi-tenant. Ele complementa RBAC, LGPD, auditoria, CSRF/CORS e as
decisões de isolamento por `organization_id`.

## Assets
- organizations, users, memberships, invites
- incidents, evidence metadata, audit logs
- edge workers, heartbeats, detections
- operational catalog: sites, cameras, zones, workers, rules, PPE
- platform admin operations and auth/session state

## Actors
- org owner/admin/manager/operator/auditor
- edge worker device
- platform admin/support
- unauthenticated external client

## Trust boundaries
- browser ↔ API
- edge worker ↔ API
- org-scoped API ↔ platform admin API
- API ↔ DB/object storage/Redis

## Main threats
- cross-tenant read/write via path params, filters, or stale cookies
- worker/org/site/camera mismatch on detections or evidence upload
- invite abuse to escalate role or cross org boundaries
- platform admin actions exposed to org users
- CSRF/origin bypass on browser mutations
- retention or notification jobs acting outside tenant scope
- data exfiltration through audit/evidence metadata listings or guessed IDs
- accidental leakage of edge worker credentials in logs, health, CI or job output

## Critical routes
- auth: `/api/v1/auth/*`
- incidents: `/api/v1/organizations/{org}/incidents*`
- evidence: `/api/v1/organizations/{org}/evidence*`
- edge workers: `/api/v1/edge-workers/*`
- invites: `/api/v1/organizations/{org}/invites*`, `/api/v1/invites/accept`
- platform: `/api/v1/platform/*`
- catalog: `services/operations.py` and persistence repositories

## Threat matrix

| Threat | Boundary | Mitigation | Automated check |
| --- | --- | --- | --- |
| Tenant A guesses Tenant B incident/evidence IDs | Browser ↔ API | membership + permission dependencies bind route `organization_id` to active membership | `test_tenant_isolation_http.py` cross-tenant incidents/evidence |
| Edge device submits detection for another org/site/camera | Edge worker ↔ API | edge auth plus worker org/site/camera catalog checks | edge worker mismatch tests |
| Browser mutation without CSRF or trusted origin | Browser ↔ API | CSRF cookie/header pairing + Origin/Referer validation | CSRF/origin negative tests |
| Org user calls platform admin APIs | Org API ↔ platform API | `require_platform_role` guard | platform route forbidden test |
| Catalog entities are linked across tenants | API/service ↔ catalog repository | repository `_assert_org` and scope helpers | operations service negative tests |
| Jobs purge or notify outside tenant scope | API ↔ jobs/services | jobs require `organization_id` and reuse tenant-scoped services | jobs service tests + residual risk below |

## Mitigations and tests
- membership/permission checks on org routes
- platform-role guard on platform routes
- repo/service tenant assertions for operational catalog and evidence
- worker org/site/camera checks in edge worker service
- CSRF + origin validation on mutating browser routes
- dedicated negative HTTP and service tests in tenant-isolation suites

## Platform admin and evidence

Platform admin routes are explicitly guarded by platform role checks and are not
a generic bypass for tenant evidence. Evidence read/download/list operations
remain org-route operations protected by tenant membership and permission checks.
Any future support workflow that lets platform support inspect evidence must add
explicit scoped authorization, reason capture and audit log entries before being
enabled.

## Residual risks accepted in MVP
- platform admin remains narrowly scoped to explicit platform roles
- evidence retention/audit is tenant-scoped but still in-process in some paths
- notifications are mock/in-memory until a persistent delivery pipeline exists
- no full STRIDE/DREAD scoring yet; this document captures the executable MVP
  threat model and must be revisited before external pilots
- CI secret scanning is lightweight and should be complemented by dedicated
  history scanners such as gitleaks/trufflehog later
