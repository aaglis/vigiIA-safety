import { apiFetch } from './client'
import type { Metadata, PageInfo } from './types'

export type EvidenceKind = 'snapshot' | 'clip' | 'metadata' | (string & {})

export interface EvidenceItem {
  file_id: string
  organization_id: string
  incident_id: string
  object_key: string
  media_type: string
  size: number
  source: string
  uploaded_by: string
  kind: EvidenceKind
  created_at: string
  deleted_at: string | null
  metadata: Metadata
}

export interface EvidenceListParams {
  limit?: number
  offset?: number
}

export interface EvidenceListResponse {
  items: EvidenceItem[]
  page_info: PageInfo
}

export interface EvidenceDownloadResponse {
  bucket: string
  object_key: string
  download_url: string
  expires_at: string
}

export function listEvidence(organizationId: string, incidentId: string, params: EvidenceListParams = {}) {
  const query = new URLSearchParams({ incident_id: incidentId })
  query.set('limit', String(params.limit ?? 50))
  query.set('offset', String(params.offset ?? 0))
  return apiFetch<EvidenceListResponse>(`/organizations/${organizationId}/evidence?${query.toString()}`)
}

export function getEvidenceDownloadUrl(organizationId: string, incidentId: string, fileId: string) {
  return apiFetch<EvidenceDownloadResponse>(`/organizations/${organizationId}/incidents/${incidentId}/evidence/${fileId}:download-url`, {
    method: 'POST',
  })
}
