import { apiFetch, toJsonBody } from './client'

export interface EvidenceRetentionPolicy {
  organization_id: string
  metadata_days: number
  snapshot_days: number
  clip_days: number
  audit_log_days: number
  updated_at?: string
}

export interface EvidenceAuditLogEntry {
  id: string
  organization_id: string
  actor_user_id: string
  action: string
  incident_id: string
  file_id: string
  created_at: string
  metadata: Record<string, unknown>
}

export interface EvidencePurgePreviewItem {
  incident_id: string
  file_id: string
  object_key: string
}

export interface EvidenceRetentionInput {
  metadata_days?: number | null
  snapshot_days?: number | null
  clip_days?: number | null
  audit_log_days?: number | null
  reason?: string | null
}

export interface EvidencePurgeInput {
  confirm: boolean
  reason?: string | null
}

export interface PageResponse<T> {
  items: T[]
  page_info?: { limit: number; offset: number; total: number; has_next: boolean }
}

export function getEvidenceRetentionPolicy(organizationId: string) { return apiFetch<EvidenceRetentionPolicy>(`/organizations/${organizationId}/evidence/retention`) }
export function updateEvidenceRetentionPolicy(organizationId: string, payload: EvidenceRetentionInput) { return apiFetch<EvidenceRetentionPolicy>(`/organizations/${organizationId}/evidence/retention`, { method: 'PUT', body: toJsonBody({ metadata_days: payload.metadata_days ?? null, snapshot_days: payload.snapshot_days ?? null, clip_days: payload.clip_days ?? null, audit_log_days: payload.audit_log_days ?? null, reason: payload.reason ?? null }) }) }
export function previewEvidencePurge(organizationId: string, params: { limit?: number; offset?: number } = {}) { const query = new URLSearchParams(); query.set('limit', String(params.limit ?? 50)); query.set('offset', String(params.offset ?? 0)); return apiFetch<PageResponse<EvidencePurgePreviewItem>>(`/organizations/${organizationId}/evidence/purge-preview?${query.toString()}`) }
export function listEvidenceAuditLogs(organizationId: string, params: { limit?: number; offset?: number; incident_id?: string; file_id?: string; action?: string } = {}) { const query = new URLSearchParams(); query.set('limit', String(params.limit ?? 50)); query.set('offset', String(params.offset ?? 0)); if (params.incident_id) query.set('incident_id', params.incident_id); if (params.file_id) query.set('file_id', params.file_id); if (params.action) query.set('action', params.action); return apiFetch<PageResponse<EvidenceAuditLogEntry>>(`/organizations/${organizationId}/evidence/audit-logs?${query.toString()}`) }
export function purgeExpiredEvidence(organizationId: string, payload: EvidencePurgeInput) { return apiFetch<{ organization_id: string; purged: string[]; count: number }>(`/organizations/${organizationId}/evidence/purge`, { method: 'POST', body: toJsonBody({ confirm: payload.confirm, reason: payload.reason ?? null }) }) }
