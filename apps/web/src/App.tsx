import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Outlet, useLocation, useNavigate } from '@tanstack/react-router'
import type { MeResponse } from './api/auth'
import { login, me } from './api/auth'
import { ApiError, isApiError, isSessionError } from './api/client'
import type { OperationCatalog, OperationEntityStatus, OperationZoneType } from './api/operations'
import { getCameraLiveTicket, getOperationsCatalog } from './api/operations'
import { captureLiveFrame } from './components/operations/whep'
import type { AuditLogEntry, Incident, IncidentStatus } from './api/incidents'
import { acknowledgeIncident, dismissIncident, getIncident, getIncidentAuditLog, listIncidents, resolveIncident } from './api/incidents'
import type { EvidenceItem } from './api/evidence'
import { getEvidenceDownloadUrl, listEvidence } from './api/evidence'
import { getCurrentEdgeWorkerConfig, registerEdgeWorker } from './api/edgeWorkers'
import { demoEmail, demoPassword, demoState, demoEvidenceByIncident, demoOperationsCatalog, demoOrganization } from './demo/fixtures'
import { queryKeys } from './api/queryKeys'
import { OverviewPage } from './pages/authenticated/OverviewPage'
import type { OverviewSite } from './pages/authenticated/OverviewPage'
import { EvidencePage } from './pages/authenticated/EvidencePage'
import { AuditPage } from './pages/authenticated/AuditPage'
import { IncidentsPage } from './pages/authenticated/IncidentsPage'
import { SettingsPage } from './pages/authenticated/SettingsPage'
import { OrganizationsPage } from './pages/authenticated/OrganizationsPage'
import { UsersPage } from './pages/authenticated/UsersPage'
import { Icon } from './components/ui/icons'
import type { IconName } from './components/ui/icons'
import { useOperationMutations } from './queries/hooks'
import { type AppSection, type Screen, normalizePathname, resolveRoute, routeForCamera, routeForSection, routeForSite } from './navigation/routes'
import { OperationsProvider, type OperationsContextValue } from './pages/authenticated/operations/OperationsContext'
import { formatAgoShort, formatBytes, formatClock, formatTimestamp, initialsFrom, normalizeApiError, readMetadataValueFromUnknown, selectOrganization, shortHash } from './utils/formatters'
import { EvidenceExplorer } from './components/evidence/EvidenceExplorer'
import { Sidebar } from './components/workspace/Sidebar'
import { LandingPage } from './pages/public/LandingPage'
import { LoginPage } from './pages/public/LoginPage'
import {
  AUDIT_ACTION_LABEL,
  ENTITY_STATUS_BADGE,
  STATUS_CHIP,
  ZONE_TYPE_BADGE,
  auditActionDot,
  auditActionLabel,
  labelOperationStatus,
  labelZoneType,
  ruleSeverityBadge,
  severityMeta,
} from './components/status/status'
import {
  type IncidentFilters,
  type IncidentPeriod,
  defaultIncidentFilters,
  formatDateInput,
  incidentFiltersToParams,
  incidentMatchesFilters,
  normalizeIncidentFilters,
  readIncidentFiltersFromUrl,
  writeIncidentFiltersToUrl,
} from './incidents/filters'
type ConnectionMode = 'live' | 'demo' | null

// Intervalo do refresh automático de incidentes, em ms. 0 (ou negativo) desliga.
const incidentRefreshIntervalMs = Number(import.meta.env.VITE_INCIDENT_REFRESH_MS ?? 8000)


export default function App() {
  const queryClient = useQueryClient()
  const location = useLocation()
  const navigate = useNavigate()
  const [mode, setMode] = useState<ConnectionMode>(null)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [booting, setBooting] = useState(true)
  const [banner, setBanner] = useState<string | null>(null)
  const [loginEmail, setLoginEmail] = useState(demoEmail)
  const [loginPassword, setLoginPassword] = useState(demoPassword)
  const [loginLoading, setLoginLoading] = useState(false)
  const [loginError, setLoginError] = useState<string | null>(null)
  const [meData, setMeData] = useState<MeResponse | null>(null)
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null)
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([])
  const [dashboardLoading, setDashboardLoading] = useState(false)
  const [dashboardError, setDashboardError] = useState<string | null>(null)
  const [operationsCatalog, setOperationsCatalog] = useState<OperationCatalog | null>(null)
  const [operationsLoading, setOperationsLoading] = useState(false)
  const [operationsError, setOperationsError] = useState<string | null>(null)
  const [incidentFilters, setIncidentFilters] = useState<IncidentFilters>(() => readIncidentFiltersFromUrl())
  const [actionBusy, setActionBusy] = useState<'acknowledge' | 'resolve' | 'dismiss' | null>(null)
  const [incidentQuery, setIncidentQuery] = useState('')
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null)
  const [evidenceItems, setEvidenceItems] = useState<EvidenceItem[]>([])
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null)
  const [evidenceLoading, setEvidenceLoading] = useState(false)
  const [evidenceError, setEvidenceError] = useState<string | null>(null)
  const [evidenceDownloadUrl, setEvidenceDownloadUrl] = useState<string | null>(null)
  const [evidenceDownloadLoading, setEvidenceDownloadLoading] = useState(false)
  const [evidenceDownloadError, setEvidenceDownloadError] = useState<string | null>(null)
  const incidentRequestIdRef = useRef(0)

  const activeOrganization = useMemo(() => (meData ? selectOrganization(meData) : null), [meData])
  const operationMutations = useOperationMutations(activeOrganization?.id ?? null)
  const selectedIncident = useMemo(() => incidents.find((incident) => incident.id === selectedIncidentId) ?? null, [incidents, selectedIncidentId])
  const selectedEvidence = useMemo(
    () => evidenceItems.find((evidence) => evidence.file_id === selectedEvidenceId) ?? evidenceItems[0] ?? null,
    [evidenceItems, selectedEvidenceId],
  )
  const route = useMemo(() => resolveRoute(location.pathname), [location.pathname])
  const screen = route.screen
  const workspaceSection = route.section
  const operationSites = operationsCatalog?.sites ?? []
  const operationCameras = operationsCatalog?.cameras ?? []
  const operationZones = operationsCatalog?.zones ?? []
  const operationRules = operationsCatalog?.safety_rules ?? []
  const operationPpe = operationsCatalog?.required_ppe ?? []
  const filteredSiteOptions = operationSites.map((site) => ({ id: site.id, name: site.name }))
  const filteredCameraOptions = incidentFilters.siteId === 'all' ? operationCameras : operationCameras.filter((camera) => camera.site_id === incidentFilters.siteId)
  const filteredZoneOptions = (incidentFilters.siteId === 'all' ? operationZones : operationZones.filter((zone) => zone.site_id === incidentFilters.siteId)).map((zone) => ({ id: zone.id, name: zone.id }))
  const hasActiveIncidentFilters = incidentFilters.status !== 'all'
    || incidentFilters.severity !== 'all'
    || incidentFilters.siteId !== 'all'
    || incidentFilters.cameraId !== 'all'
    || incidentFilters.zoneId !== 'all'
    || incidentFilters.period !== 'all'
  const incidentSummary = useMemo(
    () => ({
      total: incidents.length,
      open: incidents.filter((incident) => incident.status === 'open').length,
      acknowledged: incidents.filter((incident) => incident.status === 'acknowledged').length,
      resolved: incidents.filter((incident) => incident.status === 'resolved').length,
    }),
    [incidents],
  )

  const goLanding = (options: { replace?: boolean } = {}) => {
    void navigate({ to: '/', replace: options.replace })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const goLogin = (options: { replace?: boolean } = {}) => {
    void navigate({ to: '/login', replace: options.replace })
  }

  const goDashboard = (section: AppSection = 'dashboard', options: { replace?: boolean } = {}) => {
    void navigate({ to: routeForSection(section), replace: options.replace })
  }

  const goSite = (siteId: string) => {
    setSelectedSiteId(siteId)
    void navigate({ to: routeForSite(siteId) })
  }

  const goCamera = (siteId: string, cameraId: string) => {
    setSelectedSiteId(siteId)
    void navigate({ to: routeForCamera(siteId, cameraId) })
  }

  const scrollToSection = (id: string) => {
    if (screen === 'login' || screen === 'dashboard') goLanding({ replace: false })
    window.setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
  }

  const resetAuthenticatedState = () => {
    setMode(null)
    setMeData(null)
    setIncidents([])
    setOperationsCatalog(null)
    setSelectedIncidentId(null)
    setAuditLog([])
    setOperationsLoading(false)
    setOperationsError(null)
    setEvidenceItems([])
    setSelectedEvidenceId(null)
    setEvidenceLoading(false)
    setEvidenceError(null)
    setEvidenceDownloadUrl(null)
    setEvidenceDownloadLoading(false)
    setEvidenceDownloadError(null)
    setDashboardError(null)
    setMobileNavOpen(false)
  }

  const clearIncidentDetailState = () => {
    setAuditLog([])
    setEvidenceItems([])
    setSelectedEvidenceId(null)
    setEvidenceLoading(false)
    setEvidenceError(null)
    setEvidenceDownloadUrl(null)
    setEvidenceDownloadLoading(false)
    setEvidenceDownloadError(null)
  }

  const refreshIncidentList = async (meResponse: MeResponse, nextFilters: IncidentFilters, preferredIncidentId?: string | null) => {
    const organization = selectOrganization(meResponse)
    if (!organization) {
      setDashboardError('Nenhuma organização ativa encontrada.')
      setBooting(false)
      return
    }

    const normalizedFilters = normalizeIncidentFilters(nextFilters)
    writeIncidentFiltersToUrl(normalizedFilters)

    const currentRequestId = ++incidentRequestIdRef.current
    const previousSelectedId = selectedIncidentId
    const previousSelectedIncident = previousSelectedId ? incidents.find((incident) => incident.id === previousSelectedId) ?? null : null
    const shouldResetSelection = previousSelectedIncident ? !incidentMatchesFilters(previousSelectedIncident, normalizedFilters) : false

    setDashboardLoading(true)
    setDashboardError(null)

    try {
      if (mode === 'demo') {
        const demoIncidents = demoState.incidents.filter((incident) => incidentMatchesFilters(incident, normalizedFilters))
        const nextSelectedId = previousSelectedId && demoIncidents.some((incident) => incident.id === previousSelectedId)
          ? previousSelectedId
          : shouldResetSelection
            ? null
            : preferredIncidentId && demoIncidents.some((incident) => incident.id === preferredIncidentId)
              ? preferredIncidentId
              : previousSelectedId
                ? null
                : demoIncidents[0]?.id ?? null

        setIncidents(demoIncidents)
        setMode('demo')
        setMeData(meResponse)
        setSelectedIncidentId(nextSelectedId)

        if (nextSelectedId) {
          await loadIncidentContext(organization.id, nextSelectedId)
        } else {
          setAuditLog([])
          clearIncidentDetailState()
        }

        return
      }

      const response = await queryClient.fetchQuery({
        queryKey: queryKeys.incidents(organization.id, { limit: 50, offset: 0, ...incidentFiltersToParams(normalizedFilters) }),
        queryFn: () => listIncidents(organization.id, { limit: 50, offset: 0, ...incidentFiltersToParams(normalizedFilters) }),
        staleTime: 10_000,
      })

      if (currentRequestId !== incidentRequestIdRef.current) return

      const items = response.items ?? []
      const nextSelectedId = previousSelectedId && items.some((incident) => incident.id === previousSelectedId)
        ? previousSelectedId
        : shouldResetSelection
          ? null
          : preferredIncidentId && items.some((incident) => incident.id === preferredIncidentId)
            ? preferredIncidentId
            : previousSelectedId
              ? null
              : items[0]?.id ?? null

      setMode('live')
      setMeData(meResponse)
      setIncidents(items)
      setSelectedIncidentId(nextSelectedId)
      setBanner(null)

      if (nextSelectedId) {
        const [incidentDetail, audit] = await Promise.all([
          queryClient.fetchQuery({ queryKey: queryKeys.incidentDetail(organization.id, nextSelectedId), queryFn: () => getIncident(organization.id, nextSelectedId), staleTime: 10_000 }),
          queryClient.fetchQuery({ queryKey: queryKeys.incidentAudit(organization.id, nextSelectedId), queryFn: () => getIncidentAuditLog(organization.id, nextSelectedId, { limit: 50, offset: 0 }), staleTime: 10_000 }),
        ])
        if (currentRequestId !== incidentRequestIdRef.current) return
        setIncidents((current) => current.map((incident) => (incident.id === incidentDetail.id ? incidentDetail : incident)))
        setSelectedIncidentId(incidentDetail.id)
        setAuditLog(audit.items ?? [])
        await loadEvidenceContext(organization.id, incidentDetail.id, currentRequestId)
      } else {
        setAuditLog([])
        clearIncidentDetailState()
      }
    } catch (error) {
      if (isSessionError(error)) {
        expireSession()
        return
      }
      setDashboardError(`Não foi possível atualizar os incidentes: ${normalizeApiError(error)}`)
    } finally {
      if (currentRequestId === incidentRequestIdRef.current) {
        setDashboardLoading(false)
      }
      setBooting(false)
    }
  }

  const activateDemo = (reason?: string) => {
    const demoIncidents = demoState.incidents.filter((incident) => incidentMatchesFilters(incident, incidentFilters))
    const selectedId = demoIncidents[0]?.id ?? null
    const demoEvidence = selectedId ? demoEvidenceByIncident[selectedId] ?? { items: [], previewUrls: {} } : { items: [], previewUrls: {} }

    setMode('demo')
    setMeData(demoState.me)
    setIncidents(demoIncidents)
    setOperationsCatalog(demoOperationsCatalog)
    setSelectedIncidentId(selectedId)
    setAuditLog(selectedId ? demoState.auditLogs[selectedId] ?? [] : [])
    setEvidenceItems(demoEvidence.items)
    setSelectedEvidenceId(demoEvidence.items[0]?.file_id ?? null)
    setOperationsLoading(false)
    setOperationsError(null)
    setEvidenceLoading(false)
    setEvidenceError(null)
    setEvidenceDownloadUrl(null)
    setEvidenceDownloadLoading(false)
    setEvidenceDownloadError(null)
    setDashboardError(null)
    goDashboard('dashboard', { replace: true })
    setBanner(reason ?? 'Modo demonstração local ativo por ação explícita do usuário.')
    setBooting(false)
  }

  const expireSession = (reason = 'Sessão expirada. Entre novamente para continuar no modo conectado.') => {
    resetAuthenticatedState()
    setBanner(reason)
    goLogin({ replace: true })
    setBooting(false)
  }

  const logout = () => {
    resetAuthenticatedState()
    setBanner(null)
    goLogin({ replace: true })
    setBooting(false)
  }

  const hydrateLiveDashboard = async (meResponse: MeResponse, preferredIncidentId?: string) => {
    const organization = selectOrganization(meResponse)
    if (!organization) {
      setOperationsError('Nenhuma organização ativa encontrada.')
      setBooting(false)
      return
    }

    setOperationsLoading(true)
    setOperationsError(null)
    try {
      const operationsResult = await queryClient.fetchQuery({
        queryKey: queryKeys.operationsCatalog(organization.id),
        queryFn: () => getOperationsCatalog(organization.id),
        staleTime: 30_000,
      }).then(
        (result) => ({ status: 'fulfilled' as const, value: result }),
        (reason) => ({ status: 'rejected' as const, reason }),
      )

      if (operationsResult.status === 'fulfilled') {
        setOperationsCatalog(operationsResult.value)
      } else if (isSessionError(operationsResult.reason)) {
        expireSession()
        return
      } else {
        setOperationsCatalog(null)
        setOperationsError(`Não foi possível carregar a configuração operacional: ${normalizeApiError(operationsResult.reason)}`)
      }
      await refreshIncidentList(meResponse, incidentFilters, preferredIncidentId ?? null)
      // Não sequestrar a rota: quem abriu/recarregou um link fundo (a página de uma câmera,
      // por exemplo) fica onde pediu. Só manda para o dashboard quem chegou sem destino.
      if (!normalizePathname(window.location.pathname).startsWith('/dashboard')) {
        goDashboard('dashboard', { replace: true })
      }
    } catch (error) {
      if (isSessionError(error)) {
        expireSession()
        return
      }
      setOperationsError(`Não foi possível carregar a configuração operacional: ${normalizeApiError(error)}`)
    } finally {
      setOperationsLoading(false)
    }
  }

  const reloadOperationsCatalog = async () => {
    if (!activeOrganization) return
    const catalog = await queryClient.fetchQuery({
      queryKey: queryKeys.operationsCatalog(activeOrganization.id),
      queryFn: () => getOperationsCatalog(activeOrganization.id),
      staleTime: 0,
    })
    setOperationsCatalog(catalog)
  }

  // Busca um frame real da câmera para servir de fundo ao editor de zona: pega a
  // evidência mais recente entre os últimos incidentes daquela câmera. Sem incidente
  // com evidência ainda, devolve null e o editor mostra o estado vazio.
  const requestLiveTicket = useCallback(async (cameraId: string): Promise<{ whep_url: string } | null> => {
    if (mode !== 'live' || !activeOrganization) return null
    try {
      return await getCameraLiveTicket(activeOrganization.id, cameraId)
    } catch (error) {
      if (isSessionError(error)) expireSession()
      return null
    }
  }, [activeOrganization, mode])

  // Fundo do editor de zona: primeiro tenta congelar um frame da câmera AO VIVO (funciona
  // em câmera recém-cadastrada, sem incidente algum, e não passa pelo cloud). Só se a
  // câmera estiver offline cai para a última evidência registrada.
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
  }, [activeOrganization, mode])

  // Atualiza só a lista de incidentes, sem tocar em seleção, loading ou URL: o refresh
  // automático não pode puxar o tapete de quem está triando um incidente.
  const refreshIncidentsInBackground = useCallback(async () => {
    if (mode !== 'live' || !activeOrganization) return
    const params = { limit: 50, offset: 0, ...incidentFiltersToParams(normalizeIncidentFilters(incidentFilters)) }
    try {
      const response = await queryClient.fetchQuery({
        queryKey: queryKeys.incidents(activeOrganization.id, params),
        queryFn: () => listIncidents(activeOrganization.id, params),
        staleTime: 0,
      })
      setIncidents(response.items ?? [])
    } catch (error) {
      if (isSessionError(error)) expireSession()
      // Demais falhas ficam silenciosas: refresh de fundo não deve poluir a tela com erro.
    }
  }, [activeOrganization, incidentFilters, mode, queryClient])

  useEffect(() => {
    if (mode !== 'live' || incidentRefreshIntervalMs <= 0) return
    let timer: number | undefined
    const stop = () => {
      if (timer !== undefined) {
        window.clearInterval(timer)
        timer = undefined
      }
    }
    const start = () => {
      if (timer === undefined) timer = window.setInterval(() => void refreshIncidentsInBackground(), incidentRefreshIntervalMs)
    }
    // Aba oculta não consome API; ao voltar, atualiza na hora e retoma o ciclo.
    const handleVisibility = () => {
      if (document.hidden) {
        stop()
        return
      }
      void refreshIncidentsInBackground()
      start()
    }
    if (!document.hidden) start()
    document.addEventListener('visibilitychange', handleVisibility)
    return () => {
      stop()
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [mode, refreshIncidentsInBackground])

  const loadIncidentContext = async (organizationId: string, incidentId: string) => {
    const requestId = mode === 'demo' ? incidentRequestIdRef.current : ++incidentRequestIdRef.current

    if (mode === 'demo') {
      setSelectedIncidentId(incidentId)
      setAuditLog(demoState.auditLogs[incidentId] ?? [])
      const demoEvidence = demoEvidenceByIncident[incidentId] ?? { items: [], previewUrls: {} }
      setEvidenceItems(demoEvidence.items)
      setSelectedEvidenceId(demoEvidence.items[0]?.file_id ?? null)
      setEvidenceLoading(false)
      setEvidenceError(null)
      setEvidenceDownloadUrl(null)
      setEvidenceDownloadLoading(false)
      setEvidenceDownloadError(null)
      return
    }

    setDashboardLoading(true)
    setDashboardError(null)
    try {
      const [incidentDetail, audit] = await Promise.all([
        queryClient.fetchQuery({ queryKey: queryKeys.incidentDetail(organizationId, incidentId), queryFn: () => getIncident(organizationId, incidentId), staleTime: 10_000 }),
        queryClient.fetchQuery({ queryKey: queryKeys.incidentAudit(organizationId, incidentId), queryFn: () => getIncidentAuditLog(organizationId, incidentId, { limit: 50, offset: 0 }), staleTime: 10_000 }),
      ])
      if (requestId !== incidentRequestIdRef.current) return
      setIncidents((current) => current.map((incident) => (incident.id === incidentDetail.id ? incidentDetail : incident)))
      setSelectedIncidentId(incidentDetail.id)
      setAuditLog(audit.items ?? [])
      await loadEvidenceContext(organizationId, incidentDetail.id, requestId)
    } catch (error) {
      if (isSessionError(error)) {
        expireSession()
        return
      }
      setDashboardError(`Não foi possível carregar o contexto do incidente: ${normalizeApiError(error)}`)
    } finally {
      if (requestId === incidentRequestIdRef.current) {
        setDashboardLoading(false)
      }
    }
  }

  const loadEvidenceContext = async (organizationId: string, incidentId: string, requestId?: number) => {
    setEvidenceLoading(true)
    setEvidenceError(null)
    setEvidenceDownloadError(null)
    setEvidenceDownloadUrl(null)

    try {
      if (mode === 'demo') {
        const demoEvidence = demoEvidenceByIncident[incidentId] ?? { items: [], previewUrls: {} }
        setEvidenceItems(demoEvidence.items)
        setSelectedEvidenceId(demoEvidence.items[0]?.file_id ?? null)
        return
      }

      const response = await queryClient.fetchQuery({ queryKey: queryKeys.evidence(organizationId, incidentId), queryFn: () => listEvidence(organizationId, incidentId), staleTime: 10_000 })
      if (requestId !== undefined && requestId !== incidentRequestIdRef.current) return
      const items = response.items ?? []
      setEvidenceItems(items)
      setSelectedEvidenceId(items[0]?.file_id ?? null)
    } catch (error) {
      if (isSessionError(error)) {
        setEvidenceError('Sessão expirada para evidências. Entre novamente para ver os anexos.')
        return
      }
      setEvidenceItems([])
      setSelectedEvidenceId(null)
      setEvidenceError(`Não foi possível carregar as evidências: ${normalizeApiError(error)}`)
    } finally {
      if (requestId === undefined || requestId === incidentRequestIdRef.current) {
        setEvidenceLoading(false)
      }
    }
  }

  const openSelectedEvidence = async () => {
    if (!activeOrganization || !selectedIncident || !selectedEvidence) return

    setEvidenceDownloadLoading(true)
    setEvidenceDownloadError(null)

    try {
      if (mode === 'demo') {
        const preview = demoEvidenceByIncident[selectedIncident.id]?.previewUrls[selectedEvidence.file_id]
        if (!preview) {
          setEvidenceDownloadError('Esta evidência demo não tem pré-visualização segura.')
          return
        }
        setEvidenceDownloadUrl(preview)
        return
      }

      const response = await getEvidenceDownloadUrl(activeOrganization.id, selectedIncident.id, selectedEvidence.file_id)
      setEvidenceDownloadUrl(response.download_url)
    } catch (error) {
      if (isSessionError(error)) {
        expireSession()
        return
      }
      setEvidenceDownloadError(`Não foi possível abrir a evidência: ${normalizeApiError(error)}`)
    } finally {
      setEvidenceDownloadLoading(false)
    }
  }

  const selectEvidence = (fileId: string) => {
    setSelectedEvidenceId(fileId)
    setEvidenceDownloadError(null)
    if (fileId !== selectedEvidenceId) {
      setEvidenceDownloadUrl(null)
    }
  }

  const handleAction = async (action: 'acknowledge' | 'resolve' | 'dismiss') => {
    if (!activeOrganization || !selectedIncident) return
    setActionBusy(action)
    setDashboardError(null)

    try {
      if (mode === 'demo') {
        const nextStatus: IncidentStatus = action === 'acknowledge' ? 'acknowledged' : action === 'resolve' ? 'resolved' : 'dismissed'
        const updated: Incident = {
          ...selectedIncident,
          status: nextStatus,
          updated_at: new Date().toISOString(),
          acknowledged_at: nextStatus === 'acknowledged' ? new Date().toISOString() : selectedIncident.acknowledged_at,
          resolved_at: nextStatus === 'resolved' ? new Date().toISOString() : selectedIncident.resolved_at,
          dismissed_at: nextStatus === 'dismissed' ? new Date().toISOString() : selectedIncident.dismissed_at,
        }
        setIncidents((current) => current.map((incident) => (incident.id === updated.id ? updated : incident)))
        setAuditLog((current) => [
          {
            id: `demo-${Date.now()}`,
            organization_id: demoOrganization.id,
            incident_id: updated.id,
            action: `incident.${nextStatus}`,
            from_status: selectedIncident.status,
            to_status: nextStatus,
            actor: 'operator',
            created_at: updated.updated_at,
            metadata: { source: 'demo' },
          },
          ...current,
        ])
        setSelectedIncidentId(updated.id)
        return
      }

      const updated = action === 'acknowledge'
        ? await acknowledgeIncident(activeOrganization.id, selectedIncident.id)
        : action === 'resolve'
          ? await resolveIncident(activeOrganization.id, selectedIncident.id)
          : await dismissIncident(activeOrganization.id, selectedIncident.id)

      setIncidents((current) => current.map((incident) => (incident.id === updated.id ? updated : incident)))
      await loadIncidentContext(activeOrganization.id, updated.id)
    } catch (error) {
      if (isSessionError(error)) {
        expireSession()
        return
      }
      setDashboardError(`Não foi possível processar a ação: ${normalizeApiError(error)}`)
    } finally {
      setActionBusy(null)
    }
  }

  const handleLogin = async (options: { forceDemo?: boolean; email?: string; password?: string } = {}) => {
    const email = options.email ?? loginEmail.trim()
    const password = options.password ?? loginPassword
    const forceDemo = options.forceDemo ?? false

    setLoginError(null)
    setLoginLoading(true)

    try {
      if (forceDemo) {
        activateDemo('Modo demonstração local ativado manualmente.')
        return
      }

      const loginResponse = await login({ email, password })
      const meResponse = await me().catch(() => loginResponse.me)
      setBanner(null)
      goDashboard('dashboard', { replace: true })
      await hydrateLiveDashboard(meResponse)
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : 'Não foi possível entrar.')
    } finally {
      setLoginLoading(false)
    }
  }

  const updateIncidentFilters = (patch: Partial<IncidentFilters>) => {
    const nextFilters = normalizeIncidentFilters({ ...incidentFilters, ...patch })
    const nextSelectedIncident = selectedIncident

    if (nextSelectedIncident && !incidentMatchesFilters(nextSelectedIncident, nextFilters)) {
      setSelectedIncidentId(null)
      setAuditLog([])
      clearIncidentDetailState()
    }

    setIncidentFilters(nextFilters)
    if (meData) {
      void refreshIncidentList(meData, nextFilters, selectedIncidentId)
    } else {
      writeIncidentFiltersToUrl(nextFilters)
    }
  }

  const resetIncidentFilters = () => {
    updateIncidentFilters({
      status: 'all',
      severity: 'all',
      siteId: 'all',
      cameraId: 'all',
      zoneId: 'all',
      period: 'all',
      createdFrom: '',
      createdTo: '',
    })
  }

  useEffect(() => {
    let cancelled = false

    async function bootstrap() {
      try {
        const meResponse = await me()
        if (cancelled) return
        setMeData(meResponse)
        await hydrateLiveDashboard(meResponse)
      } catch {
        if (cancelled) return
        if (typeof window !== 'undefined' && normalizePathname(window.location.pathname).startsWith('/dashboard')) {
          goLogin({ replace: true })
        }
        setBooting(false)
      }
    }

    bootstrap()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (screen !== 'dashboard') return
    setMobileNavOpen(false)
  }, [screen])

  const activeWorkspaceLabel = workspaceSection === 'dashboard'
    ? 'Dashboard'
    : workspaceSection === 'incidents'
      ? 'Incidentes'
      : workspaceSection === 'evidence'
        ? 'Evidências'
        : workspaceSection === 'operations'
          ? 'Operações/Câmeras'
          : workspaceSection === 'organizations'
            ? 'Organizações'
            : workspaceSection === 'users'
              ? 'Usuários'
              : workspaceSection === 'audit'
                ? 'Auditoria'
                : 'Configurações'

  const openWorkspaceSection = (section: AppSection) => {
    goDashboard(section)
  }

  const recentIncidents = incidents.slice(0, 4)
  const criticalIncidents = incidents.filter((incident) => incident.status !== 'resolved' && incident.severity.toLowerCase() === 'high').length
  const acknowledgementDurations = incidents
    .filter((incident) => incident.acknowledged_at && incident.created_at)
    .map((incident) => (new Date(incident.acknowledged_at as string).getTime() - new Date(incident.created_at).getTime()) / 60_000)
    .filter((value) => Number.isFinite(value) && value >= 0)
  const avgAcknowledgementMinutes = acknowledgementDurations.length > 0
    ? Math.round(acknowledgementDurations.reduce((sum, value) => sum + value, 0) / acknowledgementDurations.length)
    : null
  const activeCamerasCount = operationCameras.filter((camera) => camera.status === 'active').length
  const totalCamerasCount = operationCameras.length
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

  const renderResourcePlaceholder = (title: string, description: string, bullets: string[]) => (
    <section className="space-y-6">
      <div className="rounded-xl border border-[color:var(--line)] bg-[var(--card)] p-6">
        <p className="font-mono-ui text-[11px] uppercase tracking-[0.3em] text-[var(--accent)]">{activeWorkspaceLabel}</p>
        <h1 className="mt-3 font-display text-3xl leading-tight text-[var(--ink)] sm:text-4xl">{title}</h1>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--muted)]">{description}</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <article className="rounded-xl border border-[color:var(--line)] bg-[var(--card)] p-6">
          <p className="font-mono-ui text-[11px] uppercase tracking-[0.28em] text-[var(--accent)]">Em construção</p>
          <ul className="mt-4 space-y-3 text-sm leading-7 text-[var(--muted)]">
            {bullets.map((bullet) => (
              <li key={bullet} className="flex gap-3 rounded-lg border border-[color:var(--line)] bg-[var(--paper)] px-4 py-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-[var(--accent)]" />
                <span>{bullet}</span>
              </li>
            ))}
          </ul>
        </article>

        <aside className="rounded-xl border border-[color:var(--line)] bg-[var(--ink)] p-6 text-[var(--paper)]">
          <p className="font-mono-ui text-[11px] uppercase tracking-[0.28em] text-[rgba(245,243,239,0.7)]">Contexto</p>
          <div className="mt-4 space-y-3 text-sm leading-7 text-[rgba(245,243,239,0.84)]">
            <p>Organização ativa: {activeOrganization?.name ?? '—'}</p>
            <p>Usuário: {meData?.user.full_name ?? meData?.user.email ?? '—'}</p>
            <p>Status: {liveLabel}</p>
          </div>
          <div className="mt-6 rounded-[10px] border border-white/10 bg-white/5 p-4 text-sm text-[rgba(245,243,239,0.74)]">
            Este espaço já segue o shell autenticado, então quando a tela ganhar CRUD real a navegação continuará intacta.
          </div>
        </aside>
      </div>
    </section>
  )

  const renderIncidentsSection = () => (
    <IncidentsPage
      incidents={incidents}
      incidentSummary={incidentSummary}
      selectedIncident={selectedIncident}
      selectedIncidentId={selectedIncidentId}
      auditLog={auditLog}
      incidentFilters={incidentFilters}
      incidentQuery={incidentQuery}
      hasActiveIncidentFilters={hasActiveIncidentFilters}
      dashboardLoading={dashboardLoading}
      dashboardError={dashboardError}
      operationsLoading={operationsLoading}
      operationsCatalog={operationsCatalog}
      filteredSiteOptions={filteredSiteOptions}
      filteredCameraOptions={filteredCameraOptions}
      filteredZoneOptions={filteredZoneOptions}
      connectionTone={connectionTone}
      mode={mode}
      actionBusy={actionBusy}
      evidenceItemsCount={evidenceItems.length}
      onIncidentQueryChange={setIncidentQuery}
      onUpdateIncidentFilters={updateIncidentFilters}
      onResetIncidentFilters={resetIncidentFilters}
      onSelectIncident={(id) => activeOrganization && void loadIncidentContext(activeOrganization.id, id)}
      onLoadIncidentContext={(id) => activeOrganization && void loadIncidentContext(activeOrganization.id, id)}
      onOpenEvidence={() => void openWorkspaceSection('evidence')}
      onHandleAction={handleAction}
      onOpenWorkspaceSection={openWorkspaceSection}
    />
  )

  const renderEvidenceSection = () => (
    <EvidencePage
      selectedIncident={selectedIncident}
      openWorkspaceSection={openWorkspaceSection}
      evidenceExplorer={selectedIncident ? (
        <EvidenceExplorer
          incident={selectedIncident}
          organizationName={activeOrganization?.name ?? null}
          evidenceItems={evidenceItems}
          selectedEvidence={selectedEvidence}
          evidenceLoading={evidenceLoading}
          evidenceError={evidenceError}
          evidenceDownloadUrl={evidenceDownloadUrl}
          evidenceDownloadLoading={evidenceDownloadLoading}
          evidenceDownloadError={evidenceDownloadError}
          onSelectEvidence={selectEvidence}
          onOpenEvidence={() => void openSelectedEvidence()}
          onRetry={() => void loadEvidenceContext(activeOrganization?.id ?? selectedIncident.organization_id, selectedIncident.id)}
        />
      ) : null}
    />
  )

  const renderAuditSection = () => (
    <AuditPage
      auditLog={auditLog}
      selectedIncident={selectedIncident}
      activeOrganizationName={activeOrganization?.name ?? '—'}
      activeOrganizationId={activeOrganization?.id ?? null}
      activePermissions={meData?.active_permissions ?? []}
      canReadAudit={meData?.active_permissions.includes('audit.read') ?? false}
      openWorkspaceSection={openWorkspaceSection}
    />
  )

  const renderSettingsSection = () => (
    <SettingsPage
      userName={meData?.user.full_name ?? meData?.user.email ?? '—'}
      userEmail={meData?.user.email ?? '—'}
      organizationName={activeOrganization?.name ?? 'Organização ativa'}
      organizationId={activeOrganization?.id ?? null}
      activePermissions={meData?.active_permissions ?? []}
      liveLabel={liveLabel}
    />
  )

  const connectionTone = mode === 'live'
    ? { label: 'Conectado', bg: '#E7F1EB', border: '#CFE6DA', color: '#2F7D57', dot: '#2F7D57' }
    : mode === 'demo'
      ? { label: 'Demonstração', bg: '#F3E9D6', border: '#E7D6B4', color: '#946416', dot: '#C98A2B' }
      : { label: 'Aguardando', bg: '#ECE7DF', border: '#E2DDD4', color: '#6B655C', dot: '#A9A398' }

  // Operações são rotas de verdade (sites → site → câmera): o App só provê os dados e o
  // router monta o componente de cada nível pelo <Outlet /> do layout.
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
    activePermissions: meData?.active_permissions ?? [],
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
  }), [operationSites, operationCameras, operationZones, operationRules, operationPpe, operationsLoading, operationsCatalog, activeCamerasCount, incidents, connectionTone, mode, meData, activeOrganization, loadCameraFrame, requestLiveTicket])

  const renderWorkspaceContent = () => {
    switch (workspaceSection) {
      case 'dashboard':
        return (
          <OverviewPage
            incidentSummary={incidentSummary}
            criticalIncidents={criticalIncidents}
            avgAcknowledgementMinutes={avgAcknowledgementMinutes}
            activeCamerasCount={activeCamerasCount}
            totalCamerasCount={totalCamerasCount}
            sitesCount={operationSites.length}
            sites={overviewSites}
            recentIncidents={recentIncidents}
            selectedIncidentId={selectedIncidentId}
            dashboardLoading={dashboardLoading}
            dashboardError={dashboardError}
            onOpenIncidents={() => openWorkspaceSection('incidents')}
            onRegisterIncident={() => openWorkspaceSection('incidents')}
            onSelectIncident={(id) => {
              setSelectedIncidentId(id)
              openWorkspaceSection('incidents')
              if (activeOrganization) {
                void loadIncidentContext(activeOrganization.id, id)
              }
            }}
          />
        )
      case 'incidents':
        return renderIncidentsSection()
      case 'evidence':
        return renderEvidenceSection()
      case 'operations':
        // O conteúdo vem do router: OperationsLayout + rota do nível (sites/site/câmera).
        return (
          <OperationsProvider value={operationsContextValue}>
            <Outlet />
          </OperationsProvider>
        )
      case 'audit':
        return renderAuditSection()
      case 'organizations':
        return (
          <OrganizationsPage
            memberships={meData?.memberships ?? []}
            activeOrganizationId={activeOrganization?.id ?? null}
            activeOrganizationName={activeOrganization?.name ?? 'Organização ativa'}
            userName={meData?.user.full_name ?? meData?.user.email ?? '—'}
            liveLabel={liveLabel}
            platformRole={meData?.user.platform_role ?? null}
            isLoading={booting && !meData}
          />
        )
      case 'users':
        return (
          <UsersPage
            memberships={meData?.memberships ?? []}
            userName={meData?.user.full_name ?? meData?.user.email ?? '—'}
            userEmail={meData?.user.email ?? '—'}
            activeOrganizationName={activeOrganization?.name ?? 'Organização ativa'}
            activeOrganizationId={activeOrganization?.id ?? null}
            activePermissions={meData?.active_permissions ?? []}
            liveLabel={liveLabel}
            isLoading={booting && !meData}
          />
        )
      case 'settings':
        return renderSettingsSection()
      default:
        return null
    }
  }

  const activeRole = meData?.memberships.find((membership) => membership.organization.id === activeOrganization?.id)?.role
    ?? meData?.memberships[0]?.role
    ?? ''
  const liveLabel = mode === 'live' ? 'Conectado à API' : mode === 'demo' ? 'Modo demonstração local' : 'Aguardando conexão'
  return (
    <main className="relative min-h-screen bg-[var(--bg)] text-[var(--ink)]">
      {screen === 'landing' && <LandingPage onLogin={() => goLogin()} onScrollToSection={scrollToSection} />}

      {screen === 'login' && (
        <LoginPage
          email={loginEmail}
          password={loginPassword}
          loading={loginLoading}
          error={loginError}
          onBack={() => goLanding()}
          onEmailChange={setLoginEmail}
          onPasswordChange={setLoginPassword}
          onSubmit={() => void handleLogin()}
          onDemoLogin={() => void handleLogin({ email: 'admin@vigia.local', password: 'change-me-dev' })}
          onLocalDemo={() => void handleLogin({ forceDemo: true })}
        />
      )}

      {screen === 'dashboard' && (
        <div className="flex h-screen overflow-hidden bg-[var(--paper)] text-[var(--ink)]">
          <aside className="hidden w-[250px] flex-none border-r border-[color:var(--border)] lg:block">
            <Sidebar
              orgName={activeOrganization?.name ?? 'Organização ativa'}
              sitesCount={operationSites.length}
              activeCamerasCount={activeCamerasCount}
              userName={meData?.user.full_name ?? meData?.user.email ?? 'Usuário'}
              userRole={activeRole ? `${activeRole.charAt(0).toUpperCase()}${activeRole.slice(1)}` : ''}
              activeSection={workspaceSection}
              openBadge={incidentSummary.open}
              connection={{ label: mode === 'live' ? 'Ambiente online' : mode === 'demo' ? 'Modo demonstração' : 'Aguardando conexão', dot: connectionTone.dot }}
              onSelect={openWorkspaceSection}
              onHome={goLanding}
              onSettings={() => openWorkspaceSection('settings')}
              onLogout={logout}
            />
          </aside>

          {mobileNavOpen ? (
            <div className="fixed inset-0 z-40 lg:hidden">
              <button type="button" aria-label="Fechar navegação" onClick={() => setMobileNavOpen(false)} className="absolute inset-0 bg-[rgba(32,27,24,0.38)]" />
              <div className="absolute left-0 top-0 h-full w-[min(84vw,280px)] border-r border-[color:var(--border)] shadow-[0_24px_80px_rgba(32,27,24,0.2)]">
                <Sidebar
                  orgName={activeOrganization?.name ?? 'Organização ativa'}
                  sitesCount={operationSites.length}
                  activeCamerasCount={activeCamerasCount}
                  userName={meData?.user.full_name ?? meData?.user.email ?? 'Usuário'}
                  userRole={activeRole ? `${activeRole.charAt(0).toUpperCase()}${activeRole.slice(1)}` : ''}
                  activeSection={workspaceSection}
                  openBadge={incidentSummary.open}
                  connection={{ label: mode === 'live' ? 'Ambiente online' : mode === 'demo' ? 'Modo demonstração' : 'Aguardando conexão', dot: connectionTone.dot }}
                  onSelect={openWorkspaceSection}
                  onHome={goLanding}
                  onSettings={() => openWorkspaceSection('settings')}
                  onLogout={logout}
                  onClose={() => setMobileNavOpen(false)}
                />
              </div>
            </div>
          ) : null}

          <div className="flex min-w-0 flex-1 flex-col">
            <header className="flex h-[61px] flex-none items-center justify-between gap-4 border-b border-[color:var(--border)] bg-[var(--card)] px-5 sm:px-6">
              <div className="flex min-w-0 items-center gap-3">
                <button type="button" onClick={() => setMobileNavOpen(true)} aria-label="Abrir navegação" className="grid h-9 w-9 flex-none place-items-center rounded-lg border border-[color:var(--line)] bg-[var(--paper)] text-[var(--muted)] lg:hidden">
                  <Icon name="menu" size={18} />
                </button>
                <div className="min-w-0">
                  <p className="truncate font-mono-ui text-[11px] tracking-[0.06em] text-[var(--nav-label)]">Início / {activeWorkspaceLabel}</p>
                  <p className="truncate font-display text-[19px] font-bold leading-none tracking-[-0.02em] text-[var(--ink)]">{activeWorkspaceLabel}</p>
                </div>
              </div>

              <div className="flex items-center gap-3 sm:gap-3.5">
                <div className="hidden h-[38px] w-[230px] items-center gap-2.5 rounded-[9px] border border-[color:var(--line)] bg-[var(--paper)] px-3 xl:flex">
                  <Icon name="search" size={16} className="flex-none text-[var(--nav-label)]" />
                  <span className="flex-1 truncate text-[13px] text-[var(--nav-label)]">Buscar incidente, câmera…</span>
                  <span className="flex-none rounded-[5px] border border-[color:var(--line)] px-[5px] py-px font-mono-ui text-[11px] text-[#bbb4a8]">⌘K</span>
                </div>
                <span className="hidden items-center gap-2 rounded-full border px-2.5 py-[5px] text-xs font-medium sm:inline-flex" style={{ background: connectionTone.bg, borderColor: connectionTone.border, color: connectionTone.color }}>
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: connectionTone.dot }} />
                  {connectionTone.label}
                </span>
                <span className="hidden h-6 w-px bg-[var(--border)] sm:block" />
                <button type="button" className="relative grid h-[38px] w-[38px] place-items-center rounded-[9px] border border-[color:var(--line)] bg-[var(--paper)] text-[var(--muted)] transition hover:text-[var(--ink)]">
                  <Icon name="bell" size={18} />
                  {incidentSummary.open > 0 ? <span className="absolute right-2 top-[7px] h-[7px] w-[7px] rounded-full border-[1.5px] border-[var(--card)] bg-[var(--accent)]" /> : null}
                </button>
                <span className="grid h-[38px] w-[38px] place-items-center rounded-[9px] bg-[var(--accent)] text-[13px] font-semibold text-white">{initialsFrom(meData?.user.full_name ?? meData?.user.email ?? 'U')}</span>
              </div>
            </header>

            <main className="flex-1 overflow-auto px-5 py-6 sm:px-8 sm:py-7 lg:px-10">
              {banner ? <div className="mx-auto mb-4 max-w-[1120px] rounded-[10px] border border-[rgba(47,125,87,0.24)] bg-[rgba(47,125,87,0.08)] px-4 py-3 text-sm text-[#236444]">{banner}</div> : null}
              {dashboardError && workspaceSection !== 'dashboard' ? <div className="mx-auto mb-4 max-w-[1120px] rounded-[10px] border border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.07)] px-4 py-3 text-sm text-[#9e4120]">{dashboardError}</div> : null}
              {operationsError ? <div className="mx-auto mb-4 max-w-[1120px] rounded-[10px] border border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.07)] px-4 py-3 text-sm text-[#9e4120]"><div className="flex flex-wrap items-center justify-between gap-3"><p>{operationsError}</p><button type="button" onClick={() => meData && void hydrateLiveDashboard(meData, selectedIncidentId ?? undefined)} className="font-medium text-[var(--ink)] underline decoration-[rgba(32,27,24,0.3)] underline-offset-4 transition hover:opacity-80">Tentar atualizar</button></div></div> : null}
              {renderWorkspaceContent()}
            </main>
          </div>
        </div>
      )}

      {booting ? <div className="pointer-events-none fixed bottom-4 right-4 rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-4 py-2 text-xs uppercase tracking-[0.24em] text-[var(--muted)] shadow-[0_12px_30px_rgba(32,27,24,0.1)]">Verificando sessão…</div> : null}
    </main>
  )
}
