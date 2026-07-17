import type { Incident, IncidentStatus } from '../../api/incidents'
import { Icon } from '../../components/ui/icons'

export type OverviewSite = {
  id: string
  name: string
  cameraCount: number
  activeCameraCount: number
  status: string
}

function formatMinutes(value: number | null) {
  if (value == null || Number.isNaN(value)) return '—'
  if (value < 1) return '< 1min'
  if (value < 60) return `${Math.round(value)}min`
  const hours = Math.floor(value / 60)
  const minutes = Math.round(value % 60)
  if (hours < 24) return `${hours}h ${minutes.toString().padStart(2, '0')}m`
  const days = Math.floor(hours / 24)
  return `${days}d ${hours % 24}h`
}

function formatAgo(value: string) {
  const diffMs = Date.now() - new Date(value).getTime()
  if (Number.isNaN(diffMs)) return '—'
  const min = Math.max(0, Math.round(diffMs / 60000))
  if (min < 1) return 'agora'
  if (min < 60) return `${min} min`
  const hours = Math.floor(min / 60)
  if (hours < 24) return `${hours}h`
  return `${Math.floor(hours / 24)}d`
}

const severityDot: Record<string, string> = {
  high: '#C1552B',
  medium: '#C98A2B',
  low: '#2F7D57',
}

function statusChip(status: IncidentStatus) {
  const map: Record<IncidentStatus, { label: string; bg: string; color: string }> = {
    open: { label: 'Aberto', bg: '#F6E4DC', color: '#B14A22' },
    acknowledged: { label: 'Reconhecido', bg: '#F3E9D6', color: '#946416' },
    resolved: { label: 'Resolvido', bg: '#E4EFE9', color: '#1F6B4A' },
    dismissed: { label: 'Descartado', bg: '#ECE7DF', color: '#6B655C' },
  }
  return map[status]
}

function siteDotColor(status: string) {
  if (status === 'active') return '#2F7D57'
  if (status === 'inactive' || status === 'suspended') return '#C1552B'
  return '#C98A2B'
}

export function OverviewPage({
  incidentSummary,
  criticalIncidents,
  avgAcknowledgementMinutes,
  activeCamerasCount,
  totalCamerasCount,
  sitesCount,
  sites,
  recentIncidents,
  selectedIncidentId,
  dashboardLoading,
  dashboardError,
  onSelectIncident,
  onOpenIncidents,
  onRegisterIncident,
}: {
  incidentSummary: { total: number; open: number; acknowledged: number; resolved: number }
  criticalIncidents: number
  avgAcknowledgementMinutes: number | null
  activeCamerasCount: number
  totalCamerasCount: number
  sitesCount: number
  sites: OverviewSite[]
  recentIncidents: Incident[]
  selectedIncidentId: string | null
  dashboardLoading: boolean
  dashboardError: string | null
  onSelectIncident: (id: string) => void
  onOpenIncidents: () => void
  onRegisterIncident: () => void
}) {
  const kpis = [
    { label: 'Incidentes abertos', value: String(incidentSummary.open), note: criticalIncidents > 0 ? `${criticalIncidents} crítico${criticalIncidents > 1 ? 's' : ''}` : `${incidentSummary.total} no total`, noteColor: criticalIncidents > 0 ? '#B14A22' : '#8E887B', dot: '#C1552B' },
    { label: 'Tempo até reconhecer', value: formatMinutes(avgAcknowledgementMinutes), note: avgAcknowledgementMinutes == null ? 'sem amostra' : 'média', noteColor: '#8E887B', dot: '#C98A2B' },
    { label: 'Câmeras ativas', value: `${activeCamerasCount}`, suffix: totalCamerasCount > 0 ? `/${totalCamerasCount}` : undefined, note: `${sitesCount} unidade${sitesCount === 1 ? '' : 's'}`, noteColor: '#8E887B', dot: '#2F7D57' },
    { label: 'Resolvidos', value: String(incidentSummary.resolved), note: `${incidentSummary.acknowledged} reconhecidos`, noteColor: '#2F7D57', dot: '#2F7D57' },
  ]

  return (
    <div className="mx-auto max-w-[1120px]">
      {/* page header */}
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-[28px] font-bold leading-none tracking-[-0.025em] text-[var(--ink)]">Visão geral</h2>
          <p className="mt-2 text-sm text-[var(--muted)]">Estado operacional em tempo real das unidades monitoradas.</p>
        </div>
        <div className="flex items-center gap-2.5">
          <button type="button" onClick={onOpenIncidents} className="flex h-[38px] items-center gap-2 rounded-[9px] border border-[color:var(--line)] bg-[var(--card)] px-3.5 text-sm font-medium text-[var(--ink)] transition hover:bg-white">
            <Icon name="bar-chart" size={16} className="text-[var(--muted-2)]" />
            Hoje
          </button>
          <button type="button" onClick={onRegisterIncident} className="flex h-[38px] items-center gap-2 rounded-[9px] bg-[var(--accent)] px-4 text-sm font-semibold text-white transition hover:bg-[var(--accent-hover)]">
            <Icon name="plus" size={16} />
            Registrar incidente
          </button>
        </div>
      </div>

      {dashboardLoading ? <p className="mb-4 text-sm text-[var(--muted)]">Atualizando dados operacionais…</p> : null}
      {dashboardError ? <div className="mb-4 rounded-[11px] border border-[rgba(193,85,43,0.2)] bg-[rgba(193,85,43,0.07)] px-4 py-3 text-sm text-[#9e4120]">{dashboardError}</div> : null}

      {/* KPI row */}
      <div className="mb-5 grid gap-3.5 sm:grid-cols-2 xl:grid-cols-4">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="rounded-[11px] border border-[color:var(--border)] bg-[var(--card)] px-[17px] py-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs text-[var(--muted-2)]">{kpi.label}</span>
              <span className="h-2 w-2 rounded-full" style={{ background: kpi.dot }} />
            </div>
            <div className="flex items-baseline gap-2">
              <span className="font-display text-[30px] font-bold leading-none text-[var(--ink)]">
                {kpi.value}
                {kpi.suffix ? <span className="text-[18px] text-[var(--nav-label)]">{kpi.suffix}</span> : null}
              </span>
              <span className="font-mono-ui text-[11px]" style={{ color: kpi.noteColor }}>{kpi.note}</span>
            </div>
          </div>
        ))}
      </div>

      {/* content grid: table + side */}
      <div className="grid gap-3.5 xl:grid-cols-[minmax(0,1fr)_320px]">
        {/* incidents table */}
        <div className="overflow-hidden rounded-xl border border-[color:var(--border)] bg-[var(--card)]">
          <div className="flex items-center justify-between border-b border-[color:var(--divider)] px-[18px] py-[15px]">
            <h3 className="font-display text-[15px] font-bold text-[var(--ink)]">Incidentes recentes</h3>
            <button type="button" onClick={onOpenIncidents} className="flex items-center gap-1.5 text-xs font-medium text-[var(--muted)] transition hover:text-[var(--accent)]">
              Ver todos
              <Icon name="chevron-right" size={13} className="text-[var(--nav-label)]" />
            </button>
          </div>

          <div className="grid grid-cols-[1.6fr_1fr_0.8fr_0.6fr] gap-3 border-b border-[color:var(--divider)] px-[18px] py-2.5 font-mono-ui text-[10px] tracking-[0.1em] text-[var(--nav-label)]">
            <span>EVENTO</span>
            <span>LOCAL</span>
            <span>STATUS</span>
            <span className="text-right">HÁ</span>
          </div>

          {recentIncidents.length === 0 ? (
            <div className="px-[18px] py-8 text-sm text-[var(--muted)]">
              {dashboardLoading ? 'Carregando incidentes…' : 'Nenhum incidente recente. Quando o worker enviar eventos, eles aparecem aqui.'}
            </div>
          ) : (
            recentIncidents.map((incident) => {
              const chip = statusChip(incident.status)
              const selected = selectedIncidentId === incident.id
              return (
                <button
                  key={incident.id}
                  type="button"
                  onClick={() => onSelectIncident(incident.id)}
                  className={`grid w-full grid-cols-[1.6fr_1fr_0.8fr_0.6fr] items-center gap-3 border-b border-[color:var(--row)] px-[18px] py-[13px] text-left transition last:border-b-0 hover:bg-[rgba(193,85,43,0.04)] ${selected ? 'bg-[rgba(193,85,43,0.05)]' : ''}`}
                >
                  <span className="flex items-center gap-2.5">
                    <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: severityDot[incident.severity.toLowerCase()] ?? '#8E887B' }} />
                    <span className="truncate text-[13px] font-medium text-[var(--ink)]">{incident.summary}</span>
                  </span>
                  <span className="truncate text-[13px] text-[var(--muted)]">{incident.site_id ?? 'Site —'} · {incident.camera_id}</span>
                  <span>
                    <span className="inline-flex rounded-md px-2.5 py-1 text-[11px] font-medium" style={{ background: chip.bg, color: chip.color }}>{chip.label}</span>
                  </span>
                  <span className="text-right font-mono-ui text-xs text-[var(--label)]">{formatAgo(incident.created_at)}</span>
                </button>
              )
            })
          )}
        </div>

        {/* side column */}
        <div className="flex flex-col gap-3.5">
          <div className="rounded-xl border border-[color:var(--border)] bg-[var(--card)] px-[17px] py-4">
            <h3 className="mb-3.5 font-display text-[15px] font-bold text-[var(--ink)]">Unidades</h3>
            <div className="flex flex-col gap-3">
              {sites.length === 0 ? (
                <p className="text-[13px] text-[var(--muted)]">Nenhuma unidade configurada.</p>
              ) : (
                sites.map((site) => (
                  <div key={site.id} className="flex items-center gap-2.5">
                    <span className="h-[7px] w-[7px] shrink-0 rounded-full" style={{ background: siteDotColor(site.status) }} />
                    <span className="flex-1 truncate text-[13px] text-[var(--ink)]">{site.name}</span>
                    <span className="font-mono-ui text-[11px] text-[var(--label)]">{site.activeCameraCount < site.cameraCount ? `${site.activeCameraCount}/${site.cameraCount}` : site.cameraCount} câm</span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-xl bg-[var(--ink)] p-[17px]">
            <p className="mb-2.5 font-mono-ui text-[10px] tracking-[0.16em] text-[#8a8178]">RESUMO DO TURNO</p>
            <p className="mb-1.5 font-display text-[26px] font-bold leading-[1.1] text-[var(--paper)]">{incidentSummary.total} incidente{incidentSummary.total === 1 ? '' : 's'}</p>
            <p className="mb-3.5 text-[13px] leading-[1.5] text-[#b7afa5]">{incidentSummary.open} aberto{incidentSummary.open === 1 ? '' : 's'} · {incidentSummary.acknowledged} reconhecido{incidentSummary.acknowledged === 1 ? '' : 's'} · {incidentSummary.resolved} resolvido{incidentSummary.resolved === 1 ? '' : 's'}.</p>
            <button type="button" onClick={onOpenIncidents} className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[var(--accent-hover)] transition hover:opacity-80">
              Ver incidentes
              <Icon name="arrow-right" size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
