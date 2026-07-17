import { useMemo } from 'react'
import type { AuditLogEntry, Incident, IncidentStatus } from '../../api/incidents'
import { Icon } from '../../components/ui/icons'

type IncidentPeriod = 'all' | '24h' | '7d' | '30d' | 'custom'

type IncidentFilters = {
  status: IncidentStatus | 'all'
  severity: string
  siteId: string
  cameraId: string
  zoneId: string
  period: IncidentPeriod
  createdFrom: string
  createdTo: string
}

type Option = { id: string; name: string }

const SEVERITY_META: Record<string, { label: string; dot: string; soft: string; text: string }> = {
  high: { label: 'Alta', dot: '#C1552B', soft: '#F6E4DC', text: '#B14A22' },
  medium: { label: 'Média', dot: '#C98A2B', soft: '#F3E9D6', text: '#946416' },
  low: { label: 'Baixa', dot: '#2F7D57', soft: '#E4EFE9', text: '#1F6B4A' },
}

const STATUS_CHIP: Record<IncidentStatus, { label: string; bg: string; color: string; dot: string }> = {
  open: { label: 'Aberto', bg: '#F6E4DC', color: '#B14A22', dot: '#C1552B' },
  acknowledged: { label: 'Reconhecido', bg: '#F3E9D6', color: '#946416', dot: '#C98A2B' },
  resolved: { label: 'Resolvido', bg: '#E4EFE9', color: '#1F6B4A', dot: '#2F7D57' },
  dismissed: { label: 'Descartado', bg: '#EEEAE3', color: '#7C756C', dot: '#A9A398' },
}

function severityMeta(severity: string) {
  return SEVERITY_META[severity.toLowerCase()] ?? { label: severity, dot: '#8E887B', soft: '#EEEAE3', text: '#7C756C' }
}

function formatTimestamp(value: string | null) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}

function formatClock(value: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' }).format(date)
}

function formatAgoShort(value: string | null) {
  if (!value) return '—'
  const diff = Date.now() - new Date(value).getTime()
  if (Number.isNaN(diff)) return '—'
  const min = Math.max(0, Math.round(diff / 60000))
  if (min < 1) return 'agora'
  if (min < 60) return `${min} min`
  const hours = Math.floor(min / 60)
  if (hours < 24) return `${hours} h`
  return `${Math.floor(hours / 24)} d`
}

function auditActionLabel(action: string) {
  const map: Record<string, string> = {
    created: 'Incidente criado',
    'incident.created': 'Incidente criado',
    'incident.acknowledged': 'Incidente reconhecido',
    'incident.resolved': 'Incidente resolvido',
    'incident.dismissed': 'Incidente descartado',
  }
  return map[action] ?? action
}

function auditActionDot(action: string) {
  if (action.includes('acknowledg')) return '#946416'
  if (action.includes('resolv')) return '#2F7D57'
  if (action.includes('dismiss')) return '#7C756C'
  return '#C1552B'
}

export function IncidentsPage({
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
  connectionTone,
  mode,
  actionBusy,
  evidenceItemsCount,
  onIncidentQueryChange,
  onUpdateIncidentFilters,
  onResetIncidentFilters,
  onSelectIncident,
  onLoadIncidentContext,
  onOpenEvidence,
  onHandleAction,
  onOpenWorkspaceSection,
}: {
  incidents: Incident[]
  incidentSummary: { total: number; open: number; acknowledged: number; resolved: number }
  selectedIncident: Incident | null
  selectedIncidentId: string | null
  auditLog: AuditLogEntry[]
  incidentFilters: IncidentFilters
  incidentQuery: string
  hasActiveIncidentFilters: boolean
  dashboardLoading: boolean
  dashboardError: string | null
  operationsLoading: boolean
  operationsCatalog: unknown | null
  filteredSiteOptions: Option[]
  filteredCameraOptions: Option[]
  filteredZoneOptions: Option[]
  connectionTone: { border: string; bg: string; color: string; dot: string }
  mode: 'live' | 'demo' | null
  actionBusy: 'acknowledge' | 'resolve' | 'dismiss' | null
  evidenceItemsCount: number
  onIncidentQueryChange: (value: string) => void
  onUpdateIncidentFilters: (patch: Partial<IncidentFilters>) => void
  onResetIncidentFilters: () => void
  onSelectIncident: (id: string) => void
  onLoadIncidentContext: (incidentId: string) => void
  onOpenEvidence: () => void
  onHandleAction: (action: 'acknowledge' | 'resolve' | 'dismiss') => void
  onOpenWorkspaceSection: (section: 'evidence' | 'incidents') => void
}) {
  const visibleIncidents = useMemo(() => {
    const q = incidentQuery.trim().toLowerCase()
    return q
      ? incidents.filter((incident) => incident.summary.toLowerCase().includes(q)
          || (incident.camera_id ?? '').toLowerCase().includes(q)
          || (incident.site_id ?? '').toLowerCase().includes(q)
          || (incident.zone_id ?? '').toLowerCase().includes(q))
      : incidents
  }, [incidentQuery, incidents])

  const dismissedCount = incidents.filter((incident) => incident.status === 'dismissed').length
  const statusSegments: Array<{ key: IncidentStatus | 'all'; label: string; count: number; color: string }> = [
    { key: 'open', label: 'Abertos', count: incidentSummary.open, color: '#B14A22' },
    { key: 'acknowledged', label: 'Reconhecidos', count: incidentSummary.acknowledged, color: '#946416' },
    { key: 'resolved', label: 'Resolvidos', count: incidentSummary.resolved, color: '#1F6B4A' },
    { key: 'dismissed', label: 'Descartados', count: dismissedCount, color: '#988F84' },
    { key: 'all', label: 'Todos', count: incidents.length, color: '#201B18' },
  ]
  const sev = selectedIncident ? severityMeta(selectedIncident.severity) : null
  const chip = selectedIncident ? STATUS_CHIP[selectedIncident.status] : null
  const confidence = selectedIncident?.confidence != null ? `${Math.round(selectedIncident.confidence * 100)}%` : null
  const timeline = useMemo(() => [...auditLog].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()), [auditLog])
  const canAck = selectedIncident?.status === 'open'
  const canResolveOrDismiss = selectedIncident?.status === 'open' || selectedIncident?.status === 'acknowledged'

  return (
    <div className="mx-auto flex max-w-[1200px] flex-col">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-[26px] font-bold leading-none tracking-[-0.025em] text-[var(--ink)]">Central de incidentes</h2>
          <p className="mt-1.5 text-sm text-[var(--muted)]">Triagem em tempo real — reconheça, resolva ou descarte cada evento detectado.</p>
        </div>
        <div className="flex items-center gap-2.5">
          <span className="inline-flex items-center gap-1.5 rounded-[9px] border px-2.5 py-[7px] text-xs font-medium" style={{ borderColor: connectionTone.border, background: connectionTone.bg, color: connectionTone.color }}>
            <span className="h-1.5 w-1.5 rounded-full pulse-dot" style={{ background: connectionTone.dot }} />
            {mode === 'live' ? 'Ao vivo' : 'Demonstração'}
          </span>
        </div>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap overflow-hidden rounded-[9px] border border-[color:var(--line)] bg-[var(--card)]">
          {statusSegments.map((segment) => {
            const active = incidentFilters.status === segment.key
            return (
              <button key={segment.key} type="button" onClick={() => onUpdateIncidentFilters({ status: segment.key })} className={`flex items-center gap-2 border-r border-[color:var(--divider)] px-3.5 py-2.5 text-[13px] transition last:border-r-0 ${active ? 'bg-[var(--nav-active-bg)] font-semibold text-[var(--nav-active-text)]' : 'text-[var(--muted)] hover:bg-[rgba(32,27,24,0.03)]'}`}>
                {segment.label}
                <span className="font-mono-ui" style={{ color: active ? '#B14A22' : segment.color }}>{segment.count}</span>
              </button>
            )
          })}
        </div>
      </div>

      <div className="mb-3.5 flex flex-wrap items-center gap-2">
        <div className="flex h-9 min-w-[220px] max-w-[300px] flex-1 items-center gap-2.5 rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-3">
          <Icon name="search" size={15} className="flex-none text-[var(--nav-label)]" />
          <input value={incidentQuery} onChange={(event) => onIncidentQueryChange(event.target.value)} placeholder="Buscar por tipo, câmera, zona…" className="w-full bg-transparent text-[13px] text-[var(--ink)] outline-none placeholder:text-[var(--nav-label)]" />
        </div>
        <select value={incidentFilters.severity} onChange={(event) => onUpdateIncidentFilters({ severity: event.target.value })} className="h-9 rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-2.5 text-[13px] text-[var(--muted)] outline-none transition focus:border-[rgba(193,85,43,0.5)]">
          <option value="all">Severidade</option>
          <option value="high">Alta</option>
          <option value="medium">Média</option>
          <option value="low">Baixa</option>
        </select>
        <select value={incidentFilters.siteId} onChange={(event) => onUpdateIncidentFilters({ siteId: event.target.value, cameraId: 'all', zoneId: 'all' })} disabled={operationsLoading && !operationsCatalog} className="h-9 max-w-[160px] rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-2.5 text-[13px] text-[var(--muted)] outline-none transition focus:border-[rgba(193,85,43,0.5)] disabled:opacity-60">
          <option value="all">Unidade</option>
          {filteredSiteOptions.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}
        </select>
        <select value={incidentFilters.cameraId} onChange={(event) => onUpdateIncidentFilters({ cameraId: event.target.value, zoneId: 'all' })} disabled={operationsLoading && !operationsCatalog} className="h-9 max-w-[150px] rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-2.5 text-[13px] text-[var(--muted)] outline-none transition focus:border-[rgba(193,85,43,0.5)] disabled:opacity-60">
          <option value="all">Câmera</option>
          {filteredCameraOptions.map((camera) => <option key={camera.id} value={camera.id}>{camera.name}</option>)}
        </select>
        <select value={incidentFilters.zoneId} onChange={(event) => onUpdateIncidentFilters({ zoneId: event.target.value })} disabled={operationsLoading && !operationsCatalog} className="h-9 max-w-[150px] rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-2.5 text-[13px] text-[var(--muted)] outline-none transition focus:border-[rgba(193,85,43,0.5)] disabled:opacity-60">
          <option value="all">Zona</option>
          {filteredZoneOptions.map((zone) => <option key={zone.id} value={zone.id}>{zone.id}</option>)}
        </select>
        <select value={incidentFilters.period} onChange={(event) => {
          const period = event.target.value as IncidentPeriod
          if (period === 'custom') {
            const fallback = { createdFrom: '', createdTo: '' }
            onUpdateIncidentFilters({ period: 'custom', createdFrom: incidentFilters.createdFrom || fallback.createdFrom, createdTo: incidentFilters.createdTo || fallback.createdTo })
            return
          }
          onUpdateIncidentFilters({ period })
        }} className="h-9 rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-2.5 text-[13px] font-medium text-[var(--ink)] outline-none transition focus:border-[rgba(193,85,43,0.5)]">
          <option value="all">Todo o período</option>
          <option value="24h">Últimas 24h</option>
          <option value="7d">Últimos 7 dias</option>
          <option value="30d">Últimos 30 dias</option>
          <option value="custom">Personalizado</option>
        </select>
        {hasActiveIncidentFilters || incidentQuery ? (
          <button type="button" onClick={onResetIncidentFilters} className="flex h-9 items-center gap-1.5 rounded-lg px-2.5 text-[13px] font-medium text-[var(--nav-active-text)] transition hover:bg-[rgba(193,85,43,0.06)]">Limpar</button>
        ) : null}
      </div>

      {incidentFilters.period === 'custom' ? (
        <div className="mb-3.5 grid gap-2 sm:grid-cols-2 sm:max-w-md">
          <input type="date" value={incidentFilters.createdFrom} onChange={(event) => onUpdateIncidentFilters({ period: 'custom', createdFrom: event.target.value })} className="h-9 rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-2.5 text-[13px] text-[var(--ink)] outline-none focus:border-[rgba(193,85,43,0.5)]" />
          <input type="date" value={incidentFilters.createdTo} onChange={(event) => onUpdateIncidentFilters({ period: 'custom', createdTo: event.target.value })} className="h-9 rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-2.5 text-[13px] text-[var(--ink)] outline-none focus:border-[rgba(193,85,43,0.5)]" />
        </div>
      ) : null}

      <div className="grid gap-3.5 xl:grid-cols-[minmax(0,1fr)_372px]">
        <div className="flex flex-col overflow-hidden rounded-xl border border-[color:var(--border)] bg-[var(--card)]">
          <div className="grid grid-cols-[20px_2fr_1.4fr_1fr_0.7fr] gap-3 border-b border-[color:var(--divider)] px-4 py-2.5 font-mono-ui text-[10px] tracking-[0.1em] text-[var(--nav-label)]">
            <span />
            <span>EVENTO</span>
            <span>LOCAL</span>
            <span>STATUS</span>
            <span className="text-right">HÁ</span>
          </div>
          <div className="flex-1">
            {dashboardLoading && incidents.length === 0 ? (
              <div className="px-4 py-8 text-sm text-[var(--muted)]">Carregando incidentes…</div>
            ) : visibleIncidents.length === 0 ? (
              <div className="px-4 py-10 text-sm leading-7 text-[var(--muted)]">
                {hasActiveIncidentFilters || incidentQuery ? 'Nenhum incidente corresponde aos filtros.' : 'Nenhum incidente registrado. Quando o worker enviar eventos, eles aparecem aqui.'}
              </div>
            ) : (
              visibleIncidents.map((incident) => {
                const sm = severityMeta(incident.severity)
                const sc = STATUS_CHIP[incident.status]
                const selected = selectedIncidentId === incident.id
                const muted = incident.status === 'dismissed'
                return (
                  <button key={incident.id} type="button" onClick={() => onSelectIncident(incident.id)} className={`relative grid w-full grid-cols-[20px_2fr_1.4fr_1fr_0.7fr] items-center gap-3 border-b border-[color:var(--row)] px-4 py-[13px] text-left transition last:border-b-0 hover:bg-[rgba(193,85,43,0.03)] ${selected ? 'bg-[#F9EEE7]' : ''} ${muted ? 'opacity-60' : ''}`}>
                    {selected ? <span className="absolute inset-y-0 left-0 w-[3px] bg-[var(--accent)]" /> : null}
                    <span className="h-[9px] w-[9px] justify-self-center rounded-full" style={{ background: sm.dot }} />
                    <span className="min-w-0">
                      <span className="block truncate text-[13px] font-semibold text-[var(--ink)]">{incident.summary}</span>
                      <span className="mt-0.5 block truncate font-mono-ui text-[10px] text-[var(--nav-label)]">{incident.id.slice(0, 12)} · {sm.label}</span>
                    </span>
                    <span className="min-w-0 text-[13px] text-[var(--muted)]">
                      <span className="block truncate">{incident.site_id ?? 'Site —'} · {incident.camera_id}</span>
                      {incident.zone_id ? <span className="block truncate text-[11px] text-[var(--nav-label)]">{incident.zone_id}</span> : null}
                    </span>
                    <span><span className="inline-flex rounded-md px-2.5 py-1 text-[11px] font-medium" style={{ background: sc.bg, color: sc.color }}>{sc.label}</span></span>
                    <span className="text-right font-mono-ui text-xs text-[var(--label)]">{formatAgoShort(incident.created_at)}</span>
                  </button>
                )
              })
            )}
          </div>
          {visibleIncidents.length > 0 ? (
            <div className="flex items-center justify-between border-t border-[color:var(--divider)] px-4 py-2.5 text-xs text-[var(--muted-2)]">
              <span>Mostrando {visibleIncidents.length} de {incidentSummary.total} incidentes</span>
              {dashboardLoading ? <span className="font-mono-ui text-[11px]">atualizando…</span> : null}
            </div>
          ) : null}
        </div>

        <div className="flex flex-col overflow-hidden rounded-xl border border-[color:var(--border)] bg-[var(--card)]">
          {selectedIncident && sev && chip ? (
            <>
              <div className="border-b border-[color:var(--divider)] px-[18px] py-4">
                <div className="mb-2.5 flex items-center justify-between gap-3">
                  <span className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-[11px] font-semibold" style={{ background: chip.bg, color: chip.color }}>
                    <span className="h-[7px] w-[7px] rounded-full" style={{ background: chip.dot }} />
                    {sev.label} · {chip.label}
                  </span>
                  <span className="font-mono-ui text-[11px] text-[var(--nav-label)]">{selectedIncident.id.slice(0, 12)}</span>
                </div>
                <h3 className="font-display text-[19px] font-bold leading-[1.15] tracking-[-0.02em] text-[var(--ink)]">{selectedIncident.summary}</h3>
                <p className="mt-1 text-[13px] text-[var(--muted-2)]">Detectado há {formatAgoShort(selectedIncident.created_at)}{confidence ? ` · confiança ${confidence}` : ''}</p>
              </div>

              <div className="border-b border-[color:var(--divider)] px-[18px] py-4">
                <div className="relative flex h-[150px] items-center justify-center overflow-hidden rounded-lg border border-[color:var(--line)] bg-[var(--divider)]">
                  <Icon name="video" size={26} className="text-[var(--muted-2)]" />
                  <span className="absolute left-2.5 top-2.5 rounded-[5px] bg-[rgba(252,250,247,0.85)] px-1.5 py-0.5 font-mono-ui text-[10px] tracking-[0.08em] text-[var(--muted-2)]">{(selectedIncident.camera_id ?? 'CÂM').toUpperCase()} · {(selectedIncident.site_id ?? 'SITE').toUpperCase()}</span>
                  <span className="absolute bottom-2.5 right-2.5 rounded-[5px] bg-[rgba(252,250,247,0.85)] px-1.5 py-0.5 font-mono-ui text-[10px] text-[var(--muted-2)]">frame · zona marcada</span>
                </div>
                <button type="button" onClick={() => onOpenWorkspaceSection('evidence')} className="mt-2.5 flex h-9 w-full items-center justify-center gap-2 rounded-[9px] border border-[color:var(--line)] bg-[var(--paper)] text-[13px] font-medium text-[var(--ink)] transition hover:bg-white">
                  <Icon name="video" size={15} className="text-[var(--muted-2)]" />
                  Abrir evidências{evidenceItemsCount > 0 ? ` (${evidenceItemsCount})` : ''}
                </button>
              </div>

              <div className="flex-1 overflow-auto px-[18px] py-4">
                <div className="mb-[18px] grid grid-cols-2 gap-x-4 gap-y-3">
                  {[
                    ['SITE', selectedIncident.site_id ?? '—'],
                    ['CÂMERA', selectedIncident.camera_id ?? '—'],
                    ['ZONA', selectedIncident.zone_id ?? '—'],
                    ['CRIADO', formatTimestamp(selectedIncident.created_at)],
                  ].map(([label, value]) => (
                    <div key={label}>
                      <p className="mb-0.5 font-mono-ui text-[10px] tracking-[0.1em] text-[var(--nav-label)]">{label}</p>
                      <p className="text-[13px] text-[var(--ink)]">{value}</p>
                    </div>
                  ))}
                </div>

                <p className="mb-3 font-mono-ui text-[10px] tracking-[0.12em] text-[var(--nav-label)]">LINHA DO TEMPO</p>
                {timeline.length === 0 ? (
                  <p className="text-[13px] text-[var(--muted-2)]">Sem registros de auditoria para este incidente.</p>
                ) : (
                  <div className="flex flex-col">
                    {timeline.map((entry, index) => {
                      const last = index === timeline.length - 1 && selectedIncident.status !== 'open'
                      const dot = entry.to_status && STATUS_CHIP[entry.to_status as IncidentStatus] ? STATUS_CHIP[entry.to_status as IncidentStatus].dot : '#C1552B'
                      return (
                        <div key={entry.id} className="flex gap-2.5">
                          <div className="flex flex-col items-center">
                            <span className="h-[9px] w-[9px] rounded-full" style={{ background: dot }} />
                            {!last ? <span className="w-[1.5px] flex-1 bg-[var(--border)]" /> : null}
                          </div>
                          <div className="pb-3.5">
                            <p className="text-[13px] font-medium text-[var(--ink)]">{auditActionLabel(entry.action)}</p>
                            <p className="font-mono-ui text-[11px] text-[var(--nav-label)]">{formatClock(entry.created_at)} · {entry.actor}</p>
                          </div>
                        </div>
                      )
                    })}
                    {selectedIncident.status === 'open' ? (
                      <div className="flex gap-2.5">
                        <div className="flex flex-col items-center">
                          <span className="h-[9px] w-[9px] rounded-full border-2 border-[color:var(--line)] bg-[var(--card)]" />
                        </div>
                        <div>
                          <p className="text-[13px] font-medium text-[var(--muted-2)]">Aguardando reconhecimento</p>
                          <p className="font-mono-ui text-[11px] text-[var(--nav-label)]">—</p>
                        </div>
                      </div>
                    ) : null}
                  </div>
                )}
              </div>

              <div className="border-t border-[color:var(--divider)] px-[18px] py-3.5">
                <button type="button" disabled={!canAck || actionBusy !== null} onClick={() => onHandleAction('acknowledge')} className="mb-2.5 flex h-[42px] w-full items-center justify-center gap-2 rounded-[9px] bg-[var(--accent)] text-sm font-semibold text-white transition hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-50">
                  {actionBusy === 'acknowledge' ? 'Reconhecendo…' : 'Reconhecer incidente'}
                </button>
                <div className="flex gap-2.5">
                  <button type="button" disabled={!canResolveOrDismiss || actionBusy !== null} onClick={() => onHandleAction('resolve')} className="h-[38px] flex-1 rounded-[9px] border border-[#CFE0D6] bg-[#EAF3EE] text-[13px] font-semibold text-[#1F6B4A] transition hover:bg-[#e0efe7] disabled:cursor-not-allowed disabled:opacity-50">{actionBusy === 'resolve' ? 'Resolvendo…' : 'Resolver'}</button>
                  <button type="button" disabled={!canResolveOrDismiss || actionBusy !== null} onClick={() => onHandleAction('dismiss')} className="h-[38px] flex-1 rounded-[9px] border border-[color:var(--line)] bg-[var(--card)] text-[13px] font-medium text-[var(--muted)] transition hover:bg-[var(--paper)] disabled:cursor-not-allowed disabled:opacity-50">{actionBusy === 'dismiss' ? 'Descartando…' : 'Descartar'}</button>
                </div>
              </div>
            </>
          ) : (
            <div className="grid flex-1 place-items-center px-6 py-16 text-center">
              <div className="max-w-xs">
                <div className="mx-auto mb-3 grid h-11 w-11 place-items-center rounded-xl border border-[color:var(--line)] bg-[var(--paper)]">
                  <Icon name="alert-triangle" size={20} className="text-[var(--muted-2)]" />
                </div>
                <p className="text-sm text-[var(--muted)]">Selecione um incidente na lista para ver detalhe, linha do tempo e ações.</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {dashboardError ? <div className="mt-3 rounded-[11px] border border-[rgba(193,85,43,0.2)] bg-[rgba(193,85,43,0.07)] px-4 py-3 text-sm text-[#9e4120]">{dashboardError}</div> : null}
    </div>
  )
}
