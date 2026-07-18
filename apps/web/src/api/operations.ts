import { apiFetch } from './client'
import type { Metadata } from './types'

export type OperationEntityStatus = 'active' | 'inactive' | 'suspended'
export type OperationZoneType = 'access' | 'restricted' | 'ppe'

export interface OperationSite {
  id: string
  organization_id: string
  name: string
  address: string | null
  status: OperationEntityStatus
  cameras: OperationCamera[]
  zones: OperationZone[]
  safety_rules: OperationSafetyRule[]
  required_ppe: OperationRequiredPPE[]
}

export interface OperationCamera {
  id: string
  organization_id: string
  site_id: string
  name: string
  /** Valor público seguro. Nunca contém usuário/senha/host/path do RTSP real. */
  display_stream_identifier?: string
  stream_source_type?: string
  /** @deprecated endpoints de Operações não devem retornar isto ao navegador. */
  stream_identifier?: string
  status: OperationEntityStatus
}

export interface OperationZone {
  id: string
  organization_id: string
  site_id: string
  camera_id: string
  zone_type: OperationZoneType
  /** Nome dado pelo operador ("Porta da Doca"). Zonas antigas podem não ter. */
  name?: string | null
  status: OperationEntityStatus
  polygon_json?: Metadata
}

export interface OperationSafetyRule {
  id: string
  organization_id: string
  site_id: string | null
  zone_id: string | null
  name: string
  status: OperationEntityStatus
  metadata: Metadata
}

export interface OperationRequiredPPE {
  id: string
  organization_id: string
  rule_id: string
  site_id: string | null
  zone_id: string | null
  item: string
  status: OperationEntityStatus
}

export interface OperationCatalog {
  organization_id: string
  sites: OperationSite[]
  cameras: OperationCamera[]
  zones: OperationZone[]
  safety_rules: OperationSafetyRule[]
  required_ppe: OperationRequiredPPE[]
}

export interface OperationListResponse<T> {
  items: T[]
}

export interface CreateSiteInput {
  name: string
  address?: string | null
  status?: OperationEntityStatus
}

export interface CreateCameraInput {
  site_id: string
  name: string
  stream_identifier: string
  status?: OperationEntityStatus
  metadata?: Metadata
}

export interface CreateZoneInput {
  site_id: string
  camera_id: string
  zone_type: OperationZoneType
  name?: string | null
  polygon_json?: Metadata
  status?: OperationEntityStatus
}

export interface UpdateSiteInput extends CreateSiteInput {}
export interface UpdateCameraInput extends Omit<CreateCameraInput, 'stream_identifier'> {
  /** Ausente/vazio mantém o stream secreto já salvo; preenchido troca a URL. */
  stream_identifier?: string
}
export interface UpdateZoneInput extends CreateZoneInput {}

function operationsPath(organizationId: string, path: string) {
  return `/organizations/${organizationId}/operations/${path}`
}

export function getOperationsCatalog(organizationId: string) {
  return apiFetch<OperationCatalog>(operationsPath(organizationId, 'catalog'))
}

export function createOperationSite(organizationId: string, payload: CreateSiteInput) {
  return apiFetch<{ site: OperationSite }>(operationsPath(organizationId, 'sites'), { method: 'POST', body: JSON.stringify({ name: payload.name, address: payload.address ?? null, status: payload.status ?? 'active' }) })
}

export function updateOperationSite(organizationId: string, siteId: string, payload: UpdateSiteInput) {
  return apiFetch<{ site: OperationSite }>(operationsPath(organizationId, `sites/${siteId}`), { method: 'PATCH', body: JSON.stringify({ name: payload.name, address: payload.address ?? null, status: payload.status ?? 'active' }) })
}

export function createOperationCamera(organizationId: string, payload: CreateCameraInput) {
  return apiFetch<{ camera: OperationCamera }>(operationsPath(organizationId, 'cameras'), { method: 'POST', body: JSON.stringify({ site_id: payload.site_id, name: payload.name, stream_identifier: payload.stream_identifier, status: payload.status ?? 'active', metadata: payload.metadata ?? {} }) })
}

export function updateOperationCamera(organizationId: string, cameraId: string, payload: UpdateCameraInput) {
  const body: Record<string, unknown> = { site_id: payload.site_id, name: payload.name, status: payload.status ?? 'active' }
  const stream = payload.stream_identifier?.trim()
  if (stream) body.stream_identifier = stream
  if (payload.metadata) body.metadata = payload.metadata
  return apiFetch<{ camera: OperationCamera }>(operationsPath(organizationId, `cameras/${cameraId}`), { method: 'PATCH', body: JSON.stringify(body) })
}

export function createOperationZone(organizationId: string, payload: CreateZoneInput) {
  return apiFetch<{ zone: OperationZone }>(operationsPath(organizationId, 'zones'), { method: 'POST', body: JSON.stringify({ site_id: payload.site_id, camera_id: payload.camera_id, zone_type: payload.zone_type, name: payload.name ?? null, polygon_json: payload.polygon_json ?? {}, status: payload.status ?? 'active' }) })
}

export function updateOperationZone(organizationId: string, zoneId: string, payload: UpdateZoneInput) {
  return apiFetch<{ zone: OperationZone }>(operationsPath(organizationId, `zones/${zoneId}`), { method: 'PATCH', body: JSON.stringify({ site_id: payload.site_id, camera_id: payload.camera_id, zone_type: payload.zone_type, name: payload.name ?? null, polygon_json: payload.polygon_json ?? {}, status: payload.status ?? 'active' }) })
}

export function listOperationSites(organizationId: string) {
  return apiFetch<OperationListResponse<OperationSite>>(operationsPath(organizationId, 'sites'))
}

export function listOperationCameras(organizationId: string) {
  return apiFetch<OperationListResponse<OperationCamera>>(operationsPath(organizationId, 'cameras'))
}

export function listOperationZones(organizationId: string) {
  return apiFetch<OperationListResponse<OperationZone>>(operationsPath(organizationId, 'zones'))
}

export function listSafetyRules(organizationId: string) {
  return apiFetch<OperationListResponse<OperationSafetyRule>>(operationsPath(organizationId, 'safety-rules'))
}

export function listRequiredPPE(organizationId: string) {
  return apiFetch<OperationListResponse<OperationRequiredPPE>>(operationsPath(organizationId, 'required-ppe'))
}

export interface CameraLiveTicket {
  camera_id: string
  protocol: string
  whep_url: string
  expires_at: string
}

export function getCameraLiveTicket(organizationId: string, cameraId: string) {
  return apiFetch<CameraLiveTicket>(`${operationsPath(organizationId, 'cameras')}/${encodeURIComponent(cameraId)}/live`)
}

export function deleteOperationSite(organizationId: string, siteId: string) {
  return apiFetch<void>(operationsPath(organizationId, `sites/${siteId}`), { method: 'DELETE' })
}

export function deleteOperationCamera(organizationId: string, cameraId: string) {
  return apiFetch<void>(operationsPath(organizationId, `cameras/${cameraId}`), { method: 'DELETE' })
}

export function deleteOperationZone(organizationId: string, zoneId: string) {
  return apiFetch<void>(operationsPath(organizationId, `zones/${zoneId}`), { method: 'DELETE' })
}
