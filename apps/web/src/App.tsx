import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from '@tanstack/react-router'
import type { MeResponse } from './api/auth'
import { login, me } from './api/auth'
import { isSessionError } from './api/client'
import type { AuditLogEntry, Incident, IncidentStatus } from './api/incidents'
import { acknowledgeIncident, dismissIncident, getIncident, getIncidentAuditLog, listIncidents, resolveIncident } from './api/incidents'
import type { EvidenceItem } from './api/evidence'
import { getEvidenceDownloadUrl, listEvidence } from './api/evidence'
import type { PageInfo } from './api/types'
import { demoEmail, demoPassword, demoState, demoEvidenceByIncident, demoOrganization } from './demo/fixtures'
import { queryKeys } from './api/queryKeys'
import { type AppSection, normalizePathname, resolveRoute, routeForCamera, routeForSection, routeForSite } from './navigation/routes'
import { initialsFrom, normalizeApiError, selectOrganization } from './utils/formatters'
import { SessionFrame } from './session/SessionFrame'
import { DashboardLayout } from './workspace/DashboardLayout'
import { WorkspaceContent } from './workspace/WorkspaceContent'
import { useOperationsController } from './workspace/useOperationsController'
import {
  type IncidentFilters,
  defaultIncidentFilters,
  incidentFiltersToParams,
  incidentMatchesFilters,
  normalizeIncidentFilters,
  readIncidentFiltersFromUrl,
  writeIncidentFiltersToUrl,
} from './incidents/filters'
type ConnectionMode = 'live' | 'demo' | null

// Intervalo do refresh automático de incidentes, em ms. 0 (ou negativo) desliga.
const incidentRefreshIntervalMs = Number(import.meta.env.VITE_INCIDENT_REFRESH_MS ?? 8000)
const incidentPageSize = 50
const evidencePageSize = 50


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
  const [incidentFilters, setIncidentFilters] = useState<IncidentFilters>(() => readIncidentFiltersFromUrl())
  const [actionBusy, setActionBusy] = useState<'acknowledge' | 'resolve' | 'dismiss' | null>(null)
  const [incidentQuery, setIncidentQuery] = useState('')
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null)
  const [incidentPageInfo, setIncidentPageInfo] = useState<PageInfo | null>(null)
  const [incidentLoadingMore, setIncidentLoadingMore] = useState(false)
  const [evidenceItems, setEvidenceItems] = useState<EvidenceItem[]>([])
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null)
  const [evidencePageInfo, setEvidencePageInfo] = useState<PageInfo | null>(null)
  const [evidenceLoadingMore, setEvidenceLoadingMore] = useState(false)
  const [evidenceLoading, setEvidenceLoading] = useState(false)
  const [evidenceError, setEvidenceError] = useState<string | null>(null)
  const [evidenceDownloadUrl, setEvidenceDownloadUrl] = useState<string | null>(null)
  const [evidenceDownloadLoading, setEvidenceDownloadLoading] = useState(false)
  const [evidenceDownloadError, setEvidenceDownloadError] = useState<string | null>(null)
  const incidentRequestIdRef = useRef(0)
  const incidentListRequestIdRef = useRef(0)

  const activeOrganization = useMemo(() => (meData ? selectOrganization(meData) : null), [meData])
  const selectedIncident = useMemo(() => incidents.find((incident) => incident.id === selectedIncidentId) ?? null, [incidents, selectedIncidentId])
  const selectedEvidence = useMemo(
    () => evidenceItems.find((evidence) => evidence.file_id === selectedEvidenceId) ?? evidenceItems[0] ?? null,
    [evidenceItems, selectedEvidenceId],
  )
  const route = useMemo(() => resolveRoute(location.pathname), [location.pathname])
  const screen = route.screen
  const workspaceSection = route.section
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
    setIncidentPageInfo(null)
    setIncidentLoadingMore(false)
    resetOperations()
    setSelectedIncidentId(null)
    setAuditLog([])
    setEvidenceItems([])
    setSelectedEvidenceId(null)
    setEvidencePageInfo(null)
    setEvidenceLoadingMore(false)
    setEvidenceLoading(false)
    setEvidenceError(null)
    setEvidenceDownloadUrl(null)
    setEvidenceDownloadLoading(false)
    setEvidenceDownloadError(null)
    setDashboardError(null)
    setMobileNavOpen(false)
    incidentRequestIdRef.current += 1
    incidentListRequestIdRef.current += 1
  }

  const clearIncidentDetailState = () => {
    setAuditLog([])
    setEvidenceItems([])
    setSelectedEvidenceId(null)
    setEvidencePageInfo(null)
    setEvidenceLoadingMore(false)
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
    incidentListRequestIdRef.current += 1

    const currentRequestId = ++incidentRequestIdRef.current
    const previousSelectedId = selectedIncidentId
    const previousSelectedIncident = previousSelectedId ? incidents.find((incident) => incident.id === previousSelectedId) ?? null : null
    const shouldResetSelection = previousSelectedIncident ? !incidentMatchesFilters(previousSelectedIncident, normalizedFilters) : false

    setDashboardLoading(true)
    setDashboardError(null)

    try {
      if (mode === 'demo') {
        const demoIncidents = demoState.incidents.filter((incident) => incidentMatchesFilters(incident, normalizedFilters))
        const demoPageInfo: PageInfo = { limit: incidentPageSize, offset: 0, total: demoIncidents.length, has_next: false }
        const nextSelectedId = previousSelectedId && demoIncidents.some((incident) => incident.id === previousSelectedId)
          ? previousSelectedId
          : shouldResetSelection
            ? null
            : preferredIncidentId && demoIncidents.some((incident) => incident.id === preferredIncidentId)
              ? preferredIncidentId
              : previousSelectedId
                ? null
                : demoIncidents[0]?.id ?? null

        if (currentRequestId !== incidentRequestIdRef.current) return

        setIncidents(demoIncidents)
        setIncidentPageInfo(demoPageInfo)
        setIncidentLoadingMore(false)
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
        queryKey: queryKeys.incidents(organization.id, { limit: incidentPageSize, offset: 0, ...incidentFiltersToParams(normalizedFilters) }),
        queryFn: () => listIncidents(organization.id, { limit: incidentPageSize, offset: 0, ...incidentFiltersToParams(normalizedFilters) }),
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
      setIncidentPageInfo(response.page_info)
      setIncidentLoadingMore(false)
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

  const loadMoreIncidents = async () => {
    if (!activeOrganization || mode !== 'live' || !incidentPageInfo?.has_next || incidentLoadingMore) return

    const currentRequestId = ++incidentListRequestIdRef.current
    const normalizedFilters = normalizeIncidentFilters(incidentFilters)
    const nextOffset = incidentPageInfo.offset + incidentPageInfo.limit

    setIncidentLoadingMore(true)

    try {
      const params = { limit: incidentPageSize, offset: nextOffset, ...incidentFiltersToParams(normalizedFilters) }
      const response = await queryClient.fetchQuery({
        queryKey: queryKeys.incidents(activeOrganization.id, params),
        queryFn: () => listIncidents(activeOrganization.id, params),
        staleTime: 10_000,
      })
      if (currentRequestId !== incidentListRequestIdRef.current) return
      const items = response.items ?? []
      setIncidents((current) => [...current, ...items])
      setIncidentPageInfo(response.page_info)
    } catch (error) {
      if (isSessionError(error)) {
        expireSession()
        return
      }
      setDashboardError(`Não foi possível carregar mais incidentes: ${normalizeApiError(error)}`)
    } finally {
      if (currentRequestId === incidentListRequestIdRef.current) {
        setIncidentLoadingMore(false)
      }
    }
  }

  const activateDemo = (reason?: string) => {
    incidentRequestIdRef.current += 1
    incidentListRequestIdRef.current += 1
    const demoIncidents = demoState.incidents.filter((incident) => incidentMatchesFilters(incident, incidentFilters))
    const selectedId = demoIncidents[0]?.id ?? null
    const demoEvidence = selectedId ? demoEvidenceByIncident[selectedId] ?? { items: [], previewUrls: {} } : { items: [], previewUrls: {} }
    const demoIncidentPageInfo: PageInfo = { limit: incidentPageSize, offset: 0, total: demoIncidents.length, has_next: false }
    const demoEvidencePageInfo: PageInfo = { limit: evidencePageSize, offset: 0, total: demoEvidence.items.length, has_next: false }

    setMode('demo')
    setMeData(demoState.me)
    setIncidents(demoIncidents)
    setIncidentPageInfo(demoIncidentPageInfo)
    setIncidentLoadingMore(false)
    activateDemoOperations()
    setSelectedIncidentId(selectedId)
    setAuditLog(selectedId ? demoState.auditLogs[selectedId] ?? [] : [])
    setEvidenceItems(demoEvidence.items)
    setEvidencePageInfo(demoEvidencePageInfo)
    setEvidenceLoadingMore(false)
    setSelectedEvidenceId(demoEvidence.items[0]?.file_id ?? null)
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
      setDashboardError('Nenhuma organização ativa encontrada.')
      setBooting(false)
      return
    }

    try {
      const operationsLoaded = await loadOperationsCatalog(organization.id)
      if (!operationsLoaded) return
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
      setDashboardError(`Não foi possível carregar o dashboard: ${normalizeApiError(error)}`)
    }
  }

  // Atualiza só a lista de incidentes, sem tocar em seleção, loading ou URL: o refresh
  // automático não pode puxar o tapete de quem está triando um incidente.
  const refreshIncidentsInBackground = useCallback(async () => {
    if (mode !== 'live' || !activeOrganization) return
    const currentRequestId = ++incidentListRequestIdRef.current
    const params = { limit: Math.max(incidents.length, incidentPageSize), offset: 0, ...incidentFiltersToParams(normalizeIncidentFilters(incidentFilters)) }
    try {
      const response = await queryClient.fetchQuery({
        queryKey: queryKeys.incidents(activeOrganization.id, params),
        queryFn: () => listIncidents(activeOrganization.id, params),
        staleTime: 0,
      })
      if (currentRequestId !== incidentListRequestIdRef.current) return
      setIncidents(response.items ?? [])
      setIncidentPageInfo(response.page_info)
    } catch (error) {
      if (isSessionError(error)) expireSession()
      // Demais falhas ficam silenciosas: refresh de fundo não deve poluir a tela com erro.
    }
  }, [activeOrganization, incidentFilters, incidents.length, mode, queryClient])

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
      setEvidencePageInfo({ limit: evidencePageSize, offset: 0, total: demoEvidence.items.length, has_next: false })
      setEvidenceLoadingMore(false)
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
    setEvidencePageInfo(null)
    setEvidenceLoadingMore(false)

    try {
      if (mode === 'demo') {
        const demoEvidence = demoEvidenceByIncident[incidentId] ?? { items: [], previewUrls: {} }
        setEvidenceItems(demoEvidence.items)
        setEvidencePageInfo({ limit: evidencePageSize, offset: 0, total: demoEvidence.items.length, has_next: false })
        setSelectedEvidenceId(demoEvidence.items[0]?.file_id ?? null)
        return
      }

      const response = await queryClient.fetchQuery({ queryKey: queryKeys.evidence(organizationId, incidentId, { limit: evidencePageSize, offset: 0 }), queryFn: () => listEvidence(organizationId, incidentId, { limit: evidencePageSize, offset: 0 }), staleTime: 10_000 })
      if (requestId !== undefined && requestId !== incidentRequestIdRef.current) return
      const items = response.items ?? []
      setEvidenceItems(items)
      setEvidencePageInfo(response.page_info)
      setSelectedEvidenceId(items[0]?.file_id ?? null)
    } catch (error) {
      if (isSessionError(error)) {
        setEvidenceError('Sessão expirada para evidências. Entre novamente para ver os anexos.')
        return
      }
      setEvidenceItems([])
      setSelectedEvidenceId(null)
      setEvidencePageInfo(null)
      setEvidenceError(`Não foi possível carregar as evidências: ${normalizeApiError(error)}`)
    } finally {
      if (requestId === undefined || requestId === incidentRequestIdRef.current) {
        setEvidenceLoading(false)
      }
    }
  }

  const loadMoreEvidence = async () => {
    if (!activeOrganization || !selectedIncident || mode !== 'live' || !evidencePageInfo?.has_next || evidenceLoadingMore) return

    const requestId = incidentRequestIdRef.current
    const nextOffset = evidencePageInfo.offset + evidencePageInfo.limit

    setEvidenceLoadingMore(true)

    try {
      const params = { limit: evidencePageSize, offset: nextOffset }
      const response = await queryClient.fetchQuery({
        queryKey: queryKeys.evidence(activeOrganization.id, selectedIncident.id, params),
        queryFn: () => listEvidence(activeOrganization.id, selectedIncident.id, params),
        staleTime: 10_000,
      })
      if (requestId !== incidentRequestIdRef.current) return
      const items = response.items ?? []
      setEvidenceItems((current) => [...current, ...items])
      setEvidencePageInfo(response.page_info)
    } catch (error) {
      if (isSessionError(error)) {
        expireSession()
        return
      }
      setEvidenceError(`Não foi possível carregar mais evidências: ${normalizeApiError(error)}`)
    } finally {
      if (requestId === incidentRequestIdRef.current) {
        setEvidenceLoadingMore(false)
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

  const connectionTone = mode === 'live'
    ? { label: 'Conectado', bg: '#E7F1EB', border: '#CFE6DA', color: '#2F7D57', dot: '#2F7D57' }
    : mode === 'demo'
      ? { label: 'Demonstração', bg: '#F3E9D6', border: '#E7D6B4', color: '#946416', dot: '#C98A2B' }
      : { label: 'Aguardando', bg: '#ECE7DF', border: '#E2DDD4', color: '#6B655C', dot: '#A9A398' }

  const operationsController = useOperationsController({
    activeOrganization,
    mode,
    incidents,
    incidentFilters,
    connectionTone,
    activePermissions: meData?.active_permissions ?? [],
    queryClient,
    expireSession,
    goSite,
    goCamera,
    goDashboard,
  })
  const {
    operationsCatalog,
    operationsLoading,
    operationsError,
    operationSites,
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
  } = operationsController

  const activeRole = meData?.memberships.find((membership) => membership.organization.id === activeOrganization?.id)?.role
    ?? meData?.memberships[0]?.role
    ?? ''
  const liveLabel = mode === 'live' ? 'Conectado à API' : mode === 'demo' ? 'Modo demonstração local' : 'Aguardando conexão'
  return (
    <SessionFrame
      screen={screen}
      booting={booting}
      loginEmail={loginEmail}
      loginPassword={loginPassword}
      loginLoading={loginLoading}
      loginError={loginError}
      onLandingLogin={() => goLogin()}
      onScrollToSection={scrollToSection}
      onLoginBack={() => goLanding()}
      onEmailChange={setLoginEmail}
      onPasswordChange={setLoginPassword}
      onLoginSubmit={() => void handleLogin()}
      onDemoLogin={() => void handleLogin({ email: 'admin@vigia.local', password: 'change-me-dev' })}
      onLocalDemo={() => void handleLogin({ forceDemo: true })}
    >
      {screen === 'dashboard' && (
        <DashboardLayout
          banner={banner}
          dashboardError={dashboardError}
          operationsError={operationsError}
          onRetryOperations={() => meData && void hydrateLiveDashboard(meData, selectedIncidentId ?? undefined)}
          activeOrganizationName={activeOrganization?.name ?? 'Organização ativa'}
          sitesCount={operationSites.length}
          activeCamerasCount={activeCamerasCount}
          userName={meData?.user.full_name ?? meData?.user.email ?? 'Usuário'}
          userRole={activeRole ? `${activeRole.charAt(0).toUpperCase()}${activeRole.slice(1)}` : ''}
          activeSection={workspaceSection}
          openBadge={incidentSummary.open}
          connection={{ label: mode === 'live' ? 'Ambiente online' : mode === 'demo' ? 'Modo demonstração' : 'Aguardando conexão', dot: connectionTone.dot }}
          connectionTone={connectionTone}
          onSelect={openWorkspaceSection}
          onHome={goLanding}
          onSettings={() => openWorkspaceSection('settings')}
          onLogout={logout}
          mobileNavOpen={mobileNavOpen}
          onOpenMobileNav={() => setMobileNavOpen(true)}
          onCloseMobileNav={() => setMobileNavOpen(false)}
          activeWorkspaceLabel={activeWorkspaceLabel}
          initials={initialsFrom(meData?.user.full_name ?? meData?.user.email ?? 'U')}
          showDashboardError={workspaceSection !== 'dashboard'}
        >
          <WorkspaceContent
            workspaceSection={workspaceSection}
            overview={{
              incidentSummary,
              criticalIncidents,
              avgAcknowledgementMinutes,
              activeCamerasCount,
              totalCamerasCount,
              sitesCount: operationSites.length,
              sites: overviewSites,
              recentIncidents,
              selectedIncidentId,
              dashboardLoading,
              dashboardError,
              onOpenIncidents: () => openWorkspaceSection('incidents'),
              onRegisterIncident: () => openWorkspaceSection('incidents'),
              onSelectIncident: (id) => {
                setSelectedIncidentId(id)
                openWorkspaceSection('incidents')
                if (activeOrganization) void loadIncidentContext(activeOrganization.id, id)
              },
            }}
            incidents={{
              incidents,
              incidentSummary,
              selectedIncident,
              selectedIncidentId,
              auditLog,
              incidentFilters,
              incidentQuery,
              hasActiveIncidentFilters,
              dashboardLoading,
              dashboardError,
              operationsLoading,
              operationsCatalog,
              filteredSiteOptions,
              filteredCameraOptions,
              filteredZoneOptions,
              incidentPageInfo,
              incidentLoadingMore,
              connectionTone,
              mode,
              actionBusy,
              evidenceItemsCount: evidenceItems.length,
              onIncidentQueryChange: setIncidentQuery,
              onUpdateIncidentFilters: updateIncidentFilters,
              onResetIncidentFilters: resetIncidentFilters,
              onSelectIncident: (id) => activeOrganization && void loadIncidentContext(activeOrganization.id, id),
              onLoadIncidentContext: (id) => activeOrganization && void loadIncidentContext(activeOrganization.id, id),
              onLoadMoreIncidents: () => void loadMoreIncidents(),
              onOpenEvidence: () => void openWorkspaceSection('evidence'),
              onHandleAction: handleAction,
              onOpenWorkspaceSection: openWorkspaceSection,
            }}
            evidence={{
              selectedIncident,
              activeOrganizationName: activeOrganization?.name ?? null,
              openWorkspaceSection,
              explorer: {
                evidenceItems,
                selectedEvidence,
                evidenceLoading,
                evidenceError,
                evidenceDownloadUrl,
                evidenceDownloadLoading,
                evidenceDownloadError,
                evidencePageInfo,
                evidenceLoadingMore,
                onSelectEvidence: selectEvidence,
                onOpenEvidence: () => void openSelectedEvidence(),
                onRetry: () => selectedIncident && void loadEvidenceContext(activeOrganization?.id ?? selectedIncident.organization_id, selectedIncident.id),
                onLoadMoreEvidence: () => void loadMoreEvidence(),
              },
            }}
            operations={{ value: operationsContextValue }}
            audit={{
              auditLog,
              selectedIncident,
              activeOrganizationName: activeOrganization?.name ?? '—',
              activeOrganizationId: activeOrganization?.id ?? null,
              activePermissions: meData?.active_permissions ?? [],
              canReadAudit: meData?.active_permissions.includes('audit.read') ?? false,
              openWorkspaceSection,
            }}
            organizations={{
              memberships: meData?.memberships ?? [],
              activeOrganizationId: activeOrganization?.id ?? null,
              activeOrganizationName: activeOrganization?.name ?? 'Organização ativa',
              userName: meData?.user.full_name ?? meData?.user.email ?? '—',
              liveLabel,
              platformRole: meData?.user.platform_role ?? null,
              isLoading: booting && !meData,
            }}
            users={{
              memberships: meData?.memberships ?? [],
              userName: meData?.user.full_name ?? meData?.user.email ?? '—',
              userEmail: meData?.user.email ?? '—',
              activeOrganizationName: activeOrganization?.name ?? 'Organização ativa',
              activeOrganizationId: activeOrganization?.id ?? null,
              activePermissions: meData?.active_permissions ?? [],
              liveLabel,
              isLoading: booting && !meData,
            }}
            settings={{
              userName: meData?.user.full_name ?? meData?.user.email ?? '—',
              userEmail: meData?.user.email ?? '—',
              organizationName: activeOrganization?.name ?? 'Organização ativa',
              organizationId: activeOrganization?.id ?? null,
              activePermissions: meData?.active_permissions ?? [],
              liveLabel,
            }}
          />
        </DashboardLayout>
      )}
    </SessionFrame>
  )
}
