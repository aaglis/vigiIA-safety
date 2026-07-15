import type { Incident } from '../../api/incidents'
import { SectionHeading, SeverityPill, StatusPill } from '../../components/ui/brand'

type HealthTone = 'good' | 'warning' | 'critical' | 'neutral'

type HealthItem = {
  label: string
  tone: HealthTone
  detail: string
}

function formatMinutes(value: number | null) {
  if (value == null || Number.isNaN(value)) return '—'
  if (value < 1) return '< 1 min'
  if (value < 60) return `${Math.round(value)} min`
  const hours = Math.floor(value / 60)
  const minutes = Math.round(value % 60)
  if (hours < 24) return `${hours}h ${minutes.toString().padStart(2, '0')}m`
  const days = Math.floor(hours / 24)
  return `${days}d ${hours % 24}h`
}

function formatTimestamp(value: string | null) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}

export function OverviewPage({
  activeOrganization,
  userName,
  incidentSummary,
  criticalIncidents,
  avgAcknowledgementMinutes,
  activeCamerasCount,
  operationSitesCount,
  evidenceAvailableCount,
  evidencePendingCount,
  recentIncidents,
  selectedIncidentId,
  liveLabel,
  dashboardLoading,
  dashboardError,
  health,
  onOpenIncidents,
  onOpenEvidence,
  onOpenOperations,
  onSelectIncident,
}: {
  activeOrganization: string
  userName: string
  incidentSummary: { total: number; open: number; acknowledged: number; resolved: number }
  criticalIncidents: number
  avgAcknowledgementMinutes: number | null
  activeCamerasCount: number
  operationSitesCount: number
  evidenceAvailableCount: number
  evidencePendingCount: number
  recentIncidents: Incident[]
  selectedIncidentId: string | null
  liveLabel: string
  dashboardLoading: boolean
  dashboardError: string | null
  health: readonly HealthItem[]
  onOpenIncidents: () => void
  onOpenEvidence: () => void
  onOpenOperations: () => void
  onSelectIncident: (id: string) => void
}) {
  const pendingQueue = recentIncidents.filter((incident) => incident.status === 'open' || incident.status === 'acknowledged')

  return (
    <section className="space-y-6">
      <div className="rounded-[34px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.92)] p-6 shadow-[0_22px_60px_rgba(32,27,24,0.08)]">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="font-mono-ui text-[11px] uppercase tracking-[0.3em] text-[var(--accent)]">Dashboard</p>
            <h1 className="mt-3 font-display text-3xl leading-tight text-[var(--ink)] sm:text-4xl">Visão geral da operação</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--muted)]">Fila de ação, saúde do sistema e incidentes recentes em uma única superfície operacional.</p>
          </div>
          <div className="rounded-[24px] border border-[color:var(--line)] bg-[var(--paper)] px-4 py-3 text-right">
            <p className="font-mono-ui text-[11px] uppercase tracking-[0.28em] text-[var(--muted)]">Organização</p>
            <p className="mt-2 font-display text-lg text-[var(--ink)]">{activeOrganization}</p>
            <p className="text-xs text-[var(--muted)]">{userName}</p>
          </div>
        </div>

        {dashboardLoading ? <p className="mt-4 text-sm text-[var(--muted)]">Atualizando dados operacionais…</p> : null}
        {dashboardError ? <div className="mt-4 rounded-[24px] border border-[rgba(193,85,43,0.2)] bg-[rgba(193,85,43,0.08)] px-4 py-3 text-sm text-[#9e4120]">{dashboardError}</div> : null}

        <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          {[
            { label: 'Incidentes abertos', value: incidentSummary.open, note: `${incidentSummary.total} no total` },
            { label: 'Críticos', value: criticalIncidents, note: 'Alta severidade em triagem' },
            { label: 'Tempo médio de reconhecimento', value: formatMinutes(avgAcknowledgementMinutes), note: avgAcknowledgementMinutes == null ? 'Sem amostra suficiente' : 'Média por incidente reconhecido' },
            { label: 'Câmeras ativas', value: activeCamerasCount, note: `${operationSitesCount} sites` },
            { label: 'Evidências', value: `${evidenceAvailableCount} disponíveis`, note: `${evidencePendingCount} pendentes` },
          ].map((item) => (
            <article key={item.label} className="rounded-[24px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.66)] p-4">
              <p className="font-mono-ui text-[11px] uppercase tracking-[0.28em] text-[var(--muted)]">{item.label}</p>
              <p className="mt-3 font-display text-3xl text-[var(--ink)]">{item.value}</p>
              <p className="mt-2 text-xs uppercase tracking-[0.22em] text-[var(--muted)]">{item.note}</p>
            </article>
          ))}
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button type="button" onClick={onOpenIncidents} className="rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-medium text-[var(--paper)] shadow-[0_16px_40px_rgba(193,85,43,0.22)] transition hover:-translate-y-0.5">Abrir incidentes</button>
          <button type="button" onClick={onOpenEvidence} className="rounded-full border border-[color:var(--line)] bg-[var(--paper)] px-5 py-3 text-sm font-medium text-[var(--ink)] transition hover:-translate-y-0.5 hover:bg-white">Ver evidências</button>
          <button type="button" onClick={onOpenOperations} className="rounded-full border border-[color:var(--line)] bg-[rgba(255,255,255,0.64)] px-5 py-3 text-sm font-medium text-[var(--ink)] transition hover:-translate-y-0.5">Operações e câmeras</button>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.07fr_0.93fr]">
        <article className="rounded-[34px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.92)] p-6 shadow-[0_22px_60px_rgba(32,27,24,0.08)]">
          <SectionHeading eyebrow="Fila de ação" title="O que precisa da equipe agora" description="Incidentes abertos e reconhecidos com atalhos diretos para a tela de triagem." />

          <div className="mt-5 space-y-3">
            {pendingQueue.length === 0 ? (
              <div className="rounded-[28px] border border-dashed border-[color:var(--line)] bg-[rgba(255,255,255,0.58)] p-6 text-sm text-[var(--muted)]">Nenhum item pendente no momento.</div>
            ) : (
              pendingQueue.map((incident) => (
                <button key={incident.id} type="button" onClick={() => onSelectIncident(incident.id)} className={`w-full rounded-[28px] border p-4 text-left transition hover:-translate-y-0.5 hover:shadow-[0_16px_36px_rgba(32,27,24,0.08)] ${selectedIncidentId === incident.id ? 'border-[rgba(193,85,43,0.35)] bg-[rgba(193,85,43,0.06)]' : 'border-[color:var(--line)] bg-[rgba(255,255,255,0.55)]'}`}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-display text-xl text-[var(--ink)]">{incident.summary}</p>
                        <StatusPill status={incident.status} />
                      </div>
                      <p className="mt-2 text-sm text-[var(--muted)]">{incident.site_id ?? 'Site não informado'} · {incident.camera_id} · Zona {incident.zone_id}</p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <SeverityPill severity={incident.severity} />
                      <span className="rounded-full border border-[color:var(--line)] bg-[rgba(255,255,255,0.7)] px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-[var(--muted)]">{incident.status === 'open' ? 'Reconhecer' : 'Resolver'}</span>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <span className="rounded-full border border-[color:var(--line)] bg-[rgba(255,255,255,0.7)] px-3 py-1 text-xs text-[var(--muted)]">Criado {formatTimestamp(incident.created_at)}</span>
                    <span className="rounded-full border border-[color:var(--line)] bg-[rgba(255,255,255,0.7)] px-3 py-1 text-xs text-[var(--muted)]">Atualizado {formatTimestamp(incident.updated_at)}</span>
                  </div>
                </button>
              ))
            )}
          </div>
        </article>

        <article className="rounded-[34px] border border-[color:var(--line)] bg-[var(--card)] p-6 shadow-[0_22px_60px_rgba(32,27,24,0.08)]">
          <p className="font-mono-ui text-[11px] uppercase tracking-[0.3em] text-[var(--accent)]">Saúde da operação</p>
          <h2 className="mt-3 font-display text-3xl leading-tight text-[var(--ink)]">Sinais do sistema</h2>
          <p className="mt-3 text-sm leading-7 text-[var(--muted)]">Os status abaixo são honestos: ficam em certo quando o dado existe e em atenção quando a plataforma ainda não confirma a condição.</p>

          <div className="mt-6 space-y-3">
            {health.map((item) => {
              const toneClass = item.tone === 'good'
                ? 'bg-[rgba(47,125,87,0.14)] text-[#236444] border-[rgba(47,125,87,0.22)]'
                : item.tone === 'warning'
                  ? 'bg-[rgba(201,138,43,0.16)] text-[#7a5314] border-[rgba(201,138,43,0.25)]'
                  : item.tone === 'critical'
                    ? 'bg-[rgba(193,85,43,0.16)] text-[#9e4120] border-[rgba(193,85,43,0.28)]'
                    : 'bg-[rgba(32,27,24,0.08)] text-[var(--muted)] border-[color:var(--line)]'

              return (
                <div key={item.label} className="rounded-[24px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.62)] p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-display text-lg text-[var(--ink)]">{item.label}</p>
                    <span className={`inline-flex rounded-full border px-3 py-1 text-[10px] font-medium uppercase tracking-[0.18em] ${toneClass}`}>{item.tone === 'good' ? 'OK' : item.tone === 'warning' ? 'Atenção' : item.tone === 'critical' ? 'Crítico' : '—'}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{item.detail}</p>
                </div>
              )
            })}
          </div>

          <div className="mt-6 rounded-[24px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.68)] p-4 text-sm text-[var(--muted)]">
            Status geral: <span className="font-medium text-[var(--ink)]">{liveLabel}</span>
          </div>
        </article>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.12fr_0.88fr]">
        <article className="rounded-[34px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.92)] p-6 shadow-[0_22px_60px_rgba(32,27,24,0.08)]">
          <SectionHeading eyebrow="Incidentes recentes" title="Últimos eventos" description="Tabela curta para revisão rápida e navegação direta para o detalhe." />

          <div className="mt-5 overflow-hidden rounded-[28px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.65)]">
            <div className="grid grid-cols-[1.3fr_0.7fr_0.7fr_0.9fr_0.7fr] gap-3 border-b border-[color:var(--line)] px-4 py-3 text-[10px] uppercase tracking-[0.24em] text-[var(--muted)]">
              <span>Resumo</span>
              <span>Status</span>
              <span>Sev.</span>
              <span>Atualizado</span>
              <span>Ação</span>
            </div>
            {recentIncidents.length === 0 ? (
              <div className="px-4 py-6 text-sm text-[var(--muted)]">Nenhum incidente recente para exibir.</div>
            ) : (
              recentIncidents.map((incident) => (
                <div key={incident.id} className={`grid grid-cols-[1.3fr_0.7fr_0.7fr_0.9fr_0.7fr] gap-3 border-b border-[color:var(--line)] px-4 py-4 last:border-b-0 ${selectedIncidentId === incident.id ? 'bg-[rgba(193,85,43,0.05)]' : ''}`}>
                  <div>
                    <p className="font-medium text-[var(--ink)]">{incident.summary}</p>
                    <p className="mt-1 text-xs text-[var(--muted)]">{incident.site_id ?? 'Site não informado'} · {incident.camera_id}</p>
                  </div>
                  <div><StatusPill status={incident.status} /></div>
                  <div><SeverityPill severity={incident.severity} /></div>
                  <div className="text-sm text-[var(--muted)]">{formatTimestamp(incident.updated_at)}</div>
                  <div>
                    <button type="button" onClick={() => onSelectIncident(incident.id)} className="rounded-full border border-[color:var(--line)] bg-[var(--paper)] px-3 py-2 text-xs font-medium text-[var(--ink)] transition hover:-translate-y-0.5 hover:bg-white">Detalhes</button>
                  </div>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="rounded-[34px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.92)] p-6 shadow-[0_22px_60px_rgba(32,27,24,0.08)]">
          <p className="font-mono-ui text-[11px] uppercase tracking-[0.3em] text-[var(--accent)]">Resumo operacional</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {[
              ['Total de incidentes', incidentSummary.total],
              ['Reconhecidos', incidentSummary.acknowledged],
              ['Resolvidos', incidentSummary.resolved],
              ['Fila atual', pendingQueue.length],
            ].map(([label, value]) => (
              <div key={label} className="rounded-[24px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.62)] p-4">
                <p className="font-mono-ui text-[10px] uppercase tracking-[0.24em] text-[var(--muted)]">{label}</p>
                <p className="mt-2 font-display text-2xl text-[var(--ink)]">{String(value)}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 rounded-[24px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.68)] p-4 text-sm leading-7 text-[var(--muted)]">
            Os KPIs refletem a base carregada no shell atual. Quando houver mais fontes de telemetria, estes blocos podem virar live charts sem mudar a navegação.
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <button type="button" onClick={onOpenIncidents} className="rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-medium text-[var(--paper)] shadow-[0_16px_40px_rgba(193,85,43,0.22)] transition hover:-translate-y-0.5">Ir para incidentes</button>
            <button type="button" onClick={onOpenOperations} className="rounded-full border border-[color:var(--line)] bg-[var(--paper)] px-5 py-3 text-sm font-medium text-[var(--ink)] transition hover:-translate-y-0.5 hover:bg-white">Ir para operações</button>
          </div>
        </article>
      </div>
    </section>
  )
}
