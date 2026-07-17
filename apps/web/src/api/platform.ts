import { apiFetch, toJsonBody } from './client'

export interface PlatformOrganization {
  id: string
  name: string
  legal_name: string
  slug?: string | null
  tax_id: string
  plan?: string | null
  status: string
  created_at?: string
  updated_at?: string
}

export interface PlatformAuditLogEntry {
  id: string
  organization_id: string | null
  actor_user_id: string
  action: string
  target_type: string
  target_id: string
  ip?: string | null
  metadata_json: Record<string, unknown>
  created_at: string
}

export interface CreateOrganizationInput {
  name: string
  legal_name: string
  tax_id: string
  plan?: string | null
  leader_email?: string | null
}

export interface PageResponse<T> {
  items: T[]
  page_info?: { limit: number; offset: number; total: number; has_next: boolean }
}

export function listPlatformOrganizations() { return apiFetch<PageResponse<PlatformOrganization>>('/platform/organizations') }
export function listPlatformAuditLogs(params: { limit?: number; offset?: number; action?: string } = {}) {
  const query = new URLSearchParams()
  query.set('limit', String(params.limit ?? 50))
  query.set('offset', String(params.offset ?? 0))
  if (params.action) query.set('action', params.action)
  return apiFetch<PageResponse<PlatformAuditLogEntry>>(`/platform/audit-logs?${query.toString()}`)
}
export function createPlatformOrganization(payload: CreateOrganizationInput) {
  return apiFetch<{ organization: PlatformOrganization }>('/platform/organizations', { method: 'POST', body: toJsonBody({ name: payload.name, legal_name: payload.legal_name, tax_id: payload.tax_id, plan: payload.plan ?? null, leader_email: payload.leader_email ?? null }) })
}
export function suspendPlatformOrganization(organizationId: string) { return apiFetch<{ organization: PlatformOrganization }>(`/platform/organizations/${organizationId}/suspend`, { method: 'POST' }) }
export function reactivatePlatformOrganization(organizationId: string) { return apiFetch<{ organization: PlatformOrganization }>(`/platform/organizations/${organizationId}/reactivate`, { method: 'POST' }) }
