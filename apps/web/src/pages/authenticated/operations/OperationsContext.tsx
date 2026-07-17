import { createContext, useContext, type ReactNode } from 'react'
import type { Incident } from '../../../api/incidents'
import type {
  OperationCamera,
  OperationCatalog,
  OperationEntityStatus,
  OperationRequiredPPE,
  OperationSafetyRule,
  OperationSite,
  OperationZone,
  OperationZoneType,
} from '../../../api/operations'
import type { EdgeWorker, EdgeWorkerConfig, RegisterEdgeWorkerResponse } from '../../../api/edgeWorkers'
import type { CreateZoneInput } from '../../../api/operations'

export type EntityStatusBadge = Record<string, { label: string; bg: string; color: string }>

/**
 * Dados e ações de Operações vindos do App. Existe porque cada nível (sites, site, câmera)
 * é uma rota própria com componente próprio: sem isto, as páginas só receberiam dados
 * descendo por props e voltaríamos a precisar de um componente pai que renderiza tudo.
 */
export type OperationsContextValue = {
  operationSites: OperationSite[]
  operationCameras: OperationCamera[]
  operationZones: OperationZone[]
  operationRules: OperationSafetyRule[]
  operationPpe: OperationRequiredPPE[]
  operationsLoading: boolean
  operationsCatalog: OperationCatalog | null
  activeCamerasCount: number
  incidents: Incident[]
  connectionTone: { border: string; bg: string; color: string; dot: string; label: string }
  mode: 'live' | 'demo' | null
  ENTITY_STATUS_BADGE: EntityStatusBadge
  ZONE_TYPE_BADGE: Record<string, { label: string; bg: string; color: string }>
  readMetadataValue: (metadata: unknown, key: string) => string | null
  ruleSeverityBadge: (severity: string | null) => { dot: string; bg: string; color: string; label: string }
  activePermissions: string[]
  onCreateSite: (payload: { name: string; address?: string | null; status?: OperationEntityStatus }) => Promise<unknown>
  onCreateCamera: (payload: { site_id: string; name: string; stream_identifier: string; status?: OperationEntityStatus }) => Promise<unknown>
  onCreateZone: (payload: CreateZoneInput) => Promise<unknown>
  onUpdateSite: (id: string, payload: { name: string; address?: string | null; status?: OperationEntityStatus }) => Promise<unknown>
  onUpdateCamera: (id: string, payload: { site_id: string; name: string; stream_identifier: string; status?: OperationEntityStatus }) => Promise<unknown>
  onUpdateZone: (id: string, payload: CreateZoneInput) => Promise<unknown>
  /** Rejeita com ApiError 409 quando há histórico apontando para o cadastro. */
  onDeleteZone: (id: string) => Promise<unknown>
  onDeleteCamera: (id: string) => Promise<unknown>
  onLoadCameraFrame?: (cameraId: string) => Promise<string | null>
  onRequestLiveTicket?: (cameraId: string) => Promise<{ whep_url: string; token?: string } | null>
  onRegisterEdgeWorker: (payload: { site_id: string; name: string; allowed_camera_ids: string[] }) => Promise<RegisterEdgeWorkerResponse>
  onCheckEdgeWorkerConfig: (payload: { client_id: string; api_key: string }) => Promise<EdgeWorkerConfig>
  onOpenSite: (siteId: string) => void
  onOpenCamera: (siteId: string, cameraId: string) => void
  onBackToSites: () => void
  onOpenIncidents: () => void
}

/** Ações do layout de Operações (cabeçalho + modais) que as rotas filhas disparam. */
export type OperationsLayoutValue = {
  openDraft: (kind: 'site' | 'camera' | 'zone') => void
  openEditSite: (site: OperationSite) => void
  openEditCamera: (camera: OperationCamera) => void
  openEditZone: (zone: OperationZone) => void
  lastEdgeWorker: EdgeWorker | null
  openEdgeWorkerRegistration: () => void
  openConfigCheck: () => void
  canRegisterEdgeWorker: boolean
}

const OperationsContext = createContext<OperationsContextValue | null>(null)
const OperationsLayoutContext = createContext<OperationsLayoutValue | null>(null)

export function OperationsProvider({ value, children }: { value: OperationsContextValue; children: ReactNode }) {
  return <OperationsContext.Provider value={value}>{children}</OperationsContext.Provider>
}

export function OperationsLayoutProvider({ value, children }: { value: OperationsLayoutValue; children: ReactNode }) {
  return <OperationsLayoutContext.Provider value={value}>{children}</OperationsLayoutContext.Provider>
}

export function useOperations(): OperationsContextValue {
  const value = useContext(OperationsContext)
  if (!value) throw new Error('useOperations precisa estar dentro de OperationsProvider')
  return value
}

export function useOperationsLayout(): OperationsLayoutValue {
  const value = useContext(OperationsLayoutContext)
  if (!value) throw new Error('useOperationsLayout precisa estar dentro de OperationsLayoutProvider')
  return value
}
