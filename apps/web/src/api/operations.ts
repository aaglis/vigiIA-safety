import { apiFetch } from './client'

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
  stream_identifier: string
  status: OperationEntityStatus
}

export interface OperationZone {
  id: string
  organization_id: string
  site_id: string
  camera_id: string
  zone_type: OperationZoneType
  status: OperationEntityStatus
}

export interface OperationSafetyRule {
  id: string
  organization_id: string
  site_id: string | null
  zone_id: string | null
  name: string
  status: OperationEntityStatus
  metadata: Record<string, unknown>
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

function operationsPath(organizationId: string, path: string) {
  return `/organizations/${organizationId}/operations/${path}`
}

export function getOperationsCatalog(organizationId: string) {
  return apiFetch<OperationCatalog>(operationsPath(organizationId, 'catalog'))
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
