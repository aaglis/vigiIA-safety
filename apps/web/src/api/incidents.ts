import { apiFetch } from './client'
import type { Metadata, PageInfo } from './types'

export type IncidentStatus = 'open' | 'acknowledged' | 'resolved' | 'dismissed'

export interface Incident {
  id: string
  organization_id: string
  site_id: string | null
  detection_event_id: string
  camera_id: string
  zone_id: string
  worker_id: string | null
  event_type: string
  severity: string
  summary: string
  confidence: number | null
  metadata: Metadata
  status: IncidentStatus
  created_at: string
  updated_at: string
  acknowledged_at: string | null
  resolved_at: string | null
  dismissed_at: string | null
}

export interface AuditLogEntry {
  id: string
  organization_id: string
  incident_id: string
  action: string
  from_status: string | null
  to_status: string
  actor: string
  created_at: string
  metadata: Metadata
}

export interface IncidentListResponse {
  items: Incident[]
  page_info: PageInfo
}

export interface AuditLogResponse {
  items: AuditLogEntry[]
  page_info: PageInfo
}

export interface IncidentListParams {
  limit?: number
  offset?: number
  status?: IncidentStatus
  site_id?: string
  camera_id?: string
  zone_id?: string
  severity?: string
  created_from?: string
  created_to?: string
}

export function listIncidents(organizationId: string, params: IncidentListParams = {}) {
  const query = new URLSearchParams()
  query.set('limit', String(params.limit ?? 50))
  query.set('offset', String(params.offset ?? 0))
  if (params.status) query.set('status', params.status)
  if (params.site_id) query.set('site_id', params.site_id)
  if (params.camera_id) query.set('camera_id', params.camera_id)
  if (params.zone_id) query.set('zone_id', params.zone_id)
  if (params.severity) query.set('severity', params.severity)
  if (params.created_from) query.set('created_from', params.created_from)
  if (params.created_to) query.set('created_to', params.created_to)
  return apiFetch<IncidentListResponse>(`/organizations/${organizationId}/incidents?${query.toString()}`)
}

export function getIncident(organizationId: string, incidentId: string) {
  return apiFetch<Incident>(`/organizations/${organizationId}/incidents/${incidentId}`)
}

export function getIncidentAuditLog(organizationId: string, incidentId: string, params: { limit?: number; offset?: number } = {}) {
  const query = new URLSearchParams()
  query.set('limit', String(params.limit ?? 50))
  query.set('offset', String(params.offset ?? 0))
  return apiFetch<AuditLogResponse>(`/organizations/${organizationId}/incidents/${incidentId}/audit-log?${query.toString()}`)
}

export function acknowledgeIncident(organizationId: string, incidentId: string) {
  return apiFetch<Incident>(`/organizations/${organizationId}/incidents/${incidentId}:acknowledge`, { method: 'POST' })
}

export function resolveIncident(organizationId: string, incidentId: string) {
  return apiFetch<Incident>(`/organizations/${organizationId}/incidents/${incidentId}:resolve`, { method: 'POST', body: JSON.stringify({ reason: 'Resolvido pelo painel operacional.' }) })
}

export function dismissIncident(organizationId: string, incidentId: string) {
  return apiFetch<Incident>(`/organizations/${organizationId}/incidents/${incidentId}:dismiss`, { method: 'POST', body: JSON.stringify({ reason: 'Descartado pelo painel operacional.' }) })
}
