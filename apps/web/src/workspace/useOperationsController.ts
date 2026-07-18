import { useCallback, useMemo, useState } from 'react'
import type { QueryClient } from '@tanstack/react-query'
import type { Incident } from '../api/incidents'
import type { OperationCatalog } from '../api/operations'
import { getCameraLiveTicket, getOperationsCatalog } from '../api/operations'
import { getEvidenceDownloadUrl, listEvidence } from '../api/evidence'
import { getCurrentEdgeWorkerConfig, registerEdgeWorker } from '../api/edgeWorkers'
import { listIncidents } from '../api/incidents'
import { captureLiveFrame } from '../components/operations/whep'
import { demoOperationsCatalog } from '../demo/fixtures'
import type { IncidentFilters } from '../incidents/filters'
import type { AppSection } from '../navigation/routes'
import type { OverviewSite } from '../pages/authenticated/OverviewPage'
import type { OperationsContextValue } from '../pages/authenticated/operations/OperationsContext'
import { useEdgeWorkers, useOperationMutations } from '../queries/hooks'
import { queryKeys } from '../api/queryKeys'
import { isSessionError } from '../api/client'
import { normalizeApiError, readMetadataValueFromUnknown } from '../utils/formatters'
import { ENTITY_STATUS_BADGE, ZONE_TYPE_BADGE, ruleSeverityBadge } from '../components/status/status'

type ConnectionMode = 'live' | 'demo' | null
type ConnectionTone = { label: string; bg: string; border: string; color: string; dot: string }
type ActiveOrganization = { id: string; name?: string } | null

type Args = {
  activeOrganization: ActiveOrganization
  mode: ConnectionMode
  incidents: Incident[]
  incidentFilters: IncidentFilters
  connectionTone: ConnectionTone
  activePermissions: string[]
  queryClient: QueryClient
  expireSession: () => void
  goSite: (siteId: string) => void
  goCamera: (siteId: string, cameraId: string) => void
  goDashboard: (section?: AppSection, options?: { replace?: boolean }) => void
}

export function useOperationsController({ activeOrganization, mode, incidents, incidentFilters, connectionTone, activePermissions, queryClient, expireSession, goSite, goCamera, goDashboard }: Args) {
  const [operationsCatalog, setOperationsCatalog] = useState<OperationCatalog | null>(null)
  const [operationsLoading, setOperationsLoading] = useState(false)
  const [operationsError, setOperationsError] = useState<string | null>(null)
  const operationMutations = useOperationMutations(activeOrganization?.id ?? null)
  const edgeWorkersQuery = useEdgeWorkers(activeOrganization?.id ?? null, mode === 'live')

  const operationSites = operationsCatalog?.sites ?? []
  const operationCameras = operationsCatalog?.cameras ?? []
  const operationZones = operationsCatalog?.zones ?? []
  const operationRules = operationsCatalog?.safety_rules ?? []
  const operationPpe = operationsCatalog?.required_ppe ?? []
  const activeCamerasCount = operationCameras.filter((camera) => camera.status === 'active').length
  const totalCamerasCount = operationCameras.length
  const filteredSiteOptions = operationSites.map((site) => ({ id: site.id, name: site.name }))
  const filteredCameraOptions = incidentFilters.siteId === 'all' ? operationCameras : operationCameras.filter((camera) => camera.site_id === incidentFilters.siteId)
  const filteredZoneOptions = (incidentFilters.siteId === 'all' ? operationZones : operationZones.filter((zone) => zone.site_id === incidentFilters.siteId)).map((zone) => ({ id: zone.id, name: zone.id }))
  const overviewSites: OverviewSite[] = operationSites.map((site) => {
    const siteCameras = operationCameras.filter((camera) => camera.site_id === site.id)
    return {
      id: site.id,
      name: site.name,
      cameraCount: siteCameras.length,
      activeCameraCount: siteCameras.filter((camera) => camera.status === 'active').length,
      status: site.status,
    }
  })

  const activateDemoOperations = useCallback(() => {
    setOperationsCatalog(demoOperationsCatalog)
    setOperationsLoading(false)
    setOperationsError(null)
  }, [])

  const resetOperations = useCallback(() => {
    setOperationsCatalog(null)
    setOperationsLoading(false)
    setOperationsError(null)
  }, [])

  const loadOperationsCatalog = useCallback(async (organizationId: string) => {
    setOperationsLoading(true)
    setOperationsError(null)
    try {
      const result = await queryClient.fetchQuery({
        queryKey: queryKeys.operationsCatalog(organizationId),
        queryFn: () => getOperationsCatalog(organizationId),
        staleTime: 30_000,
      }).then(
        (value) => ({ status: 'fulfilled' as const, value }),
        (reason) => ({ status: 'rejected' as const, reason }),
      )
      if (result.status === 'fulfilled') {
        setOperationsCatalog(result.value)
      } else if (isSessionError(result.reason)) {
        expireSession()
        return false
      } else {
        setOperationsCatalog(null)
        setOperationsError(`Não foi possível carregar a configuração operacional: ${normalizeApiError(result.reason)}`)
      }
      return true
    } catch (error) {
      if (isSessionError(error)) {
        expireSession()
        return false
      }
      setOperationsError(`Não foi possível carregar a configuração operacional: ${normalizeApiError(error)}`)
      return true
    } finally {
      setOperationsLoading(false)
    }
  }, [expireSession, queryClient])

  const reloadOperationsCatalog = useCallback(async () => {
    if (!activeOrganization) return
    const catalog = await queryClient.fetchQuery({
      queryKey: queryKeys.operationsCatalog(activeOrganization.id),
      queryFn: () => getOperationsCatalog(activeOrganization.id),
      staleTime: 0,
    })
    setOperationsCatalog(catalog)
  }, [activeOrganization, queryClient])

  const requestLiveTicket = useCallback(async (cameraId: string): Promise<{ whep_url: string } | null> => {
    if (mode !== 'live' || !activeOrganization) return null
    try {
      return await getCameraLiveTicket(activeOrganization.id, cameraId)
    } catch (error) {
      if (isSessionError(error)) expireSession()
      return null
    }
  }, [activeOrganization, expireSession, mode])

  const loadCameraFrame = useCallback(async (cameraId: string): Promise<string | null> => {
    if (mode !== 'live' || !activeOrganization) return null
    try {
      const ticket = await getCameraLiveTicket(activeOrganization.id, cameraId).catch(() => null)
      if (ticket?.whep_url) {
        const frame = await captureLiveFrame(ticket.whep_url)
        if (frame) return frame
      }
    } catch (error) {
      if (isSessionError(error)) expireSession()
    }
    try {
      const response = await listIncidents(activeOrganization.id, { limit: 5, offset: 0, camera_id: cameraId })
      for (const incident of response.items ?? []) {
        const evidence = await listEvidence(activeOrganization.id, incident.id)
        const snapshot = (evidence.items ?? []).find((item) => item.media_type?.startsWith('image/')) ?? (evidence.items ?? [])[0]
        if (!snapshot) continue
        const download = await getEvidenceDownloadUrl(activeOrganization.id, incident.id, snapshot.file_id)
        if (download.download_url) return download.download_url
      }
    } catch (error) {
      if (isSessionError(error)) expireSession()
    }
    return null
  }, [activeOrganization, expireSession, mode])

  const operationsContextValue = useMemo<OperationsContextValue>(() => ({
    operationSites,
    operationCameras,
    operationZones,
    operationRules,
    operationPpe,
    operationsLoading,
    operationsCatalog,
    activeCamerasCount,
    incidents,
    connectionTone,
    mode,
    ENTITY_STATUS_BADGE,
    ZONE_TYPE_BADGE,
    readMetadataValue: readMetadataValueFromUnknown,
    ruleSeverityBadge,
    activePermissions,
    onCreateSite: async (payload) => { await operationMutations.createSite.mutateAsync(payload); await reloadOperationsCatalog() },
    onCreateCamera: async (payload) => { await operationMutations.createCamera.mutateAsync(payload); await reloadOperationsCatalog() },
    onCreateZone: async (payload) => { await operationMutations.createZone.mutateAsync(payload); await reloadOperationsCatalog() },
    onUpdateSite: async (id, payload) => { await operationMutations.updateSite.mutateAsync({ id, payload }); await reloadOperationsCatalog() },
    onUpdateCamera: async (id, payload) => { await operationMutations.updateCamera.mutateAsync({ id, payload }); await reloadOperationsCatalog() },
    onUpdateZone: async (id, payload) => { await operationMutations.updateZone.mutateAsync({ id, payload }); await reloadOperationsCatalog() },
    onDeleteZone: async (id) => { await operationMutations.deleteZone.mutateAsync(id); await reloadOperationsCatalog() },
    onDeleteCamera: async (id) => { await operationMutations.deleteCamera.mutateAsync(id); await reloadOperationsCatalog() },
    onLoadCameraFrame: loadCameraFrame,
    onRequestLiveTicket: requestLiveTicket,
    onRegisterEdgeWorker: async (payload) => {
      if (!activeOrganization) throw new Error('Organização ativa ausente')
      return registerEdgeWorker({ organization_id: activeOrganization.id, ...payload })
    },
    onCheckEdgeWorkerConfig: async (payload) => getCurrentEdgeWorkerConfig(payload.client_id, payload.api_key),
    onOpenSite: goSite,
    onOpenCamera: goCamera,
    onBackToSites: () => goDashboard('operations'),
    onOpenIncidents: () => goDashboard('incidents'),
    edgeWorkers: edgeWorkersQuery.data?.items ?? [],
  }), [activeCamerasCount, activeOrganization, activePermissions, connectionTone, edgeWorkersQuery.data, goCamera, goDashboard, goSite, incidents, loadCameraFrame, mode, operationCameras, operationMutations, operationPpe, operationRules, operationSites, operationZones, operationsCatalog, operationsLoading, reloadOperationsCatalog, requestLiveTicket])

  return {
    operationsCatalog,
    operationsLoading,
    operationsError,
    operationSites,
    operationCameras,
    operationZones,
    operationRules,
    operationPpe,
    activeCamerasCount,
    totalCamerasCount,
    filteredSiteOptions,
    filteredCameraOptions,
    filteredZoneOptions,
    overviewSites,
    operationsContextValue,
    activateDemoOperations,
    resetOperations,
    loadOperationsCatalog,
    reloadOperationsCatalog,
  }
}
