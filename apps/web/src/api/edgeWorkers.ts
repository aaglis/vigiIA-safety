import { apiFetch, toJsonBody } from './client'
import type { JsonObject } from './types'

export interface EdgeWorker {
  id: string
  organization_id: string
  site_id: string
  name: string
  client_id: string
  allowed_camera_ids: string[]
  api_key_suffix?: string | null
  last_heartbeat_at?: string | null
  created_at?: string
  updated_at?: string
}

export interface EdgeWorkerConfig {
  worker: EdgeWorker
  capabilities: string[]
  allowed_camera_ids: string[]
}

export interface RegisterEdgeWorkerInput {
  organization_id: string
  site_id: string
  name: string
  allowed_camera_ids?: string[]
}

export interface RegisterEdgeWorkerResponse {
  worker: EdgeWorker
  api_key: string
}

export interface EdgeWorkerDetectionInput {
  event_id?: string | null
  organization_id?: string | null
  site_id?: string | null
  camera_id: string
  timestamp?: string | null
  event_type?: string
  zone_id: string
  confidence?: number | null
  model_version?: string | null
  evidence?: JsonObject | null
  severity?: string
  summary?: string | null
}

export function registerEdgeWorker(payload: RegisterEdgeWorkerInput) {
  return apiFetch<RegisterEdgeWorkerResponse>('/organizations/' + payload.organization_id + '/edge-workers', {
    method: 'POST',
    body: toJsonBody({ organization_id: payload.organization_id, site_id: payload.site_id, name: payload.name, allowed_camera_ids: payload.allowed_camera_ids ?? [] }),
  })
}

export function getCurrentEdgeWorkerConfig(clientId: string, apiKey: string) {
  return apiFetch<EdgeWorkerConfig>('/edge-workers/me/config', { headers: { 'X-Edge-Client-Id': clientId, 'X-Edge-Api-Key': apiKey } })
}

export function heartbeatEdgeWorker(clientId: string, apiKey: string) {
  return apiFetch<{ worker: EdgeWorker }>('/edge-workers/me/heartbeat', { method: 'POST', headers: { 'X-Edge-Client-Id': clientId, 'X-Edge-Api-Key': apiKey } })
}

export function submitEdgeWorkerDetection(clientId: string, apiKey: string, payload: EdgeWorkerDetectionInput) {
  return apiFetch<Record<string, unknown>>('/edge-workers/me/detections', { method: 'POST', headers: { 'X-Edge-Client-Id': clientId, 'X-Edge-Api-Key': apiKey }, body: toJsonBody({ event_id: payload.event_id ?? null, organization_id: payload.organization_id ?? null, site_id: payload.site_id ?? null, camera_id: payload.camera_id, timestamp: payload.timestamp ?? null, event_type: payload.event_type ?? 'detection', zone_id: payload.zone_id, confidence: payload.confidence ?? null, model_version: payload.model_version ?? null, evidence: payload.evidence ?? null, severity: payload.severity ?? 'medium', summary: payload.summary ?? null }) })
}

export function requestEdgeWorkerEvidenceUpload(clientId: string, apiKey: string, fileId: string) {
  const query = new URLSearchParams({ file_id: fileId })
  return apiFetch<Record<string, unknown>>(`/edge-workers/me/evidence-upload?${query.toString()}`, { method: 'POST', headers: { 'X-Edge-Client-Id': clientId, 'X-Edge-Api-Key': apiKey } })
}
