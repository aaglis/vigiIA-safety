import type { AuditLogEntry, Incident, IncidentStatus } from '../../api/incidents'
import { Button, PageHeader, TableShell } from '../../components/ui/dashboard'
import { Icon } from '../../components/ui/icons'
import { useEvidenceAuditLogs } from '../../queries/platform'

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

export function AuditPage({
  auditLog,
  selectedIncident,
  activeOrganizationName,
  activeOrganizationId,
  activePermissions,
  canReadAudit,
  openWorkspaceSection,
}: {
  auditLog: AuditLogEntry[]
  selectedIncident: Incident | null
  activeOrganizationName: string
  activeOrganizationId: string | null
  activePermissions: string[]
  canReadAudit: boolean
  openWorkspaceSection: (section: 'incidents') => void
}) {
  const evidenceAuditQuery = useEvidenceAuditLogs(activeOrganizationId, { limit: 50, offset: 0 }, canReadAudit && !!activeOrganizationId)
  const permissionLabel = activePermissions.includes('audit.read') ? 'audit.read ativo' : 'sem audit.read'
  const sorted = [...auditLog].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  const dayKey = (value: string) => new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(new Date(value))
  const groups: Array<{ day: string; entries: AuditLogEntry[] }> = []
  for (const entry of sorted) {
    const key = dayKey(entry.created_at)
    const last = groups[groups.length - 1]
    if (last && last.day === key) last.entries.push(entry)
    else groups.push({ day: key, entries: [entry] })
  }
  const hms = (value: string) => new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value))

  return (
    <div className="mx-auto max-w-[1200px]">
      <PageHeader
        eyebrow="AUDITORIA"
        title="Trilha de ações"
        description="Registro imutável de ações sensíveis para conformidade e LGPD."
        actions={<Button variant="secondary" disabled title="Pendente de API"><Icon name="download" size={15} /> Exportar (CSV/PDF)</Button>}
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="flex h-9 items-center gap-1.5 rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-3 text-[13px] text-[var(--muted)]">Organização: {activeOrganizationName ?? '—'}</span>
        <span className="ml-auto flex overflow-hidden rounded-lg border border-[color:var(--line)] text-[13px]">
          <span className="bg-[var(--nav-active-bg)] px-3 py-2 font-semibold text-[var(--nav-active-text)]">24h</span>
          <span className="border-l border-[color:var(--divider)] px-3 py-2 text-[var(--muted)]">7d</span>
          <span className="border-l border-[color:var(--divider)] px-3 py-2 text-[var(--muted)]">30d</span>
          <span className="border-l border-[color:var(--divider)] px-3 py-2 text-[var(--muted)]">Custom</span>
        </span>
      </div>

      {!canReadAudit ? (
        <div className="mb-4 rounded-xl border border-dashed border-[color:var(--line)] bg-[var(--card)] px-5 py-8">
          <p className="font-display text-lg font-bold text-[var(--ink)]">Permissão audit.read necessária</p>
          <p className="mt-2 max-w-xl text-sm leading-7 text-[var(--muted)]">A trilha de evidências só é carregada para usuários com acesso de auditoria. {permissionLabel}</p>
        </div>
      ) : evidenceAuditQuery.isLoading ? (
        <div className="mb-4 rounded-xl border border-[color:var(--line)] bg-[var(--card)] px-5 py-8 text-sm text-[var(--muted)]">Carregando auditoria de evidências…</div>
      ) : evidenceAuditQuery.isError ? (
        <div className="mb-4 rounded-xl border border-dashed border-[color:var(--line)] bg-[var(--card)] px-5 py-8">
          <p className="font-display text-lg font-bold text-[var(--ink)]">Não foi possível carregar a auditoria de evidências</p>
          <p className="mt-2 max-w-xl text-sm leading-7 text-[var(--muted)]">{evidenceAuditQuery.error instanceof Error ? evidenceAuditQuery.error.message : 'Erro desconhecido'}</p>
        </div>
      ) : evidenceAuditQuery.data?.items?.length ? (
        <TableShell title="Auditoria de evidências" description="Registros de acesso e manutenção das evidências." >
          <div className="grid grid-cols-[1.1fr_1fr_1fr_1fr] gap-3 border-b border-[color:var(--divider)] px-[18px] py-2.5 font-mono-ui text-[10px] tracking-[0.1em] text-[var(--nav-label)]">
            <span>AÇÃO</span><span>ATOR</span><span>INCIDENTE / ARQUIVO</span><span>HORA</span>
          </div>
          {evidenceAuditQuery.data.items.map((entry) => (
            <div key={entry.id} className="grid grid-cols-[1.1fr_1fr_1fr_1fr] items-center gap-3 border-b border-[color:var(--row)] px-[18px] py-3 last:border-b-0">
              <span className="truncate text-[13px] text-[var(--ink)]">{entry.action}</span>
              <span className="truncate text-[13px] text-[var(--muted)]">{entry.actor_user_id}</span>
              <span className="truncate font-mono-ui text-xs text-[var(--muted)]">{entry.incident_id} · {entry.file_id}</span>
              <span className="font-mono-ui text-xs text-[var(--muted)]">{hms(entry.created_at)}</span>
            </div>
          ))}
        </TableShell>
      ) : (
        <div className="mb-4 rounded-xl border border-dashed border-[color:var(--line)] bg-[var(--card)] px-5 py-8">
          <p className="font-display text-lg font-bold text-[var(--ink)]">Sem auditoria de evidências</p>
          <p className="mt-2 max-w-xl text-sm leading-7 text-[var(--muted)]">Nenhum registro foi retornado para a organização ativa.</p>
        </div>
      )}

      {selectedIncident && groups.length > 0 ? (
        <TableShell title="Eventos do incidente" description="Linha do tempo agrupada por data e organizada por status." >
          <div className="grid grid-cols-[88px_1.5fr_1.2fr_0.9fr_1.3fr] gap-3 border-b border-[color:var(--divider)] px-[18px] py-2.5 font-mono-ui text-[10px] tracking-[0.1em] text-[var(--nav-label)]">
            <span>HORA</span><span>AÇÃO</span><span>ATOR</span><span>INCIDENTE</span><span>TRANSIÇÃO</span>
          </div>
          {groups.map((group) => (
            <div key={group.day}>
              <div className="flex items-center gap-2.5 border-b border-[color:var(--divider)] bg-[#F2EEE7] px-[18px] py-2.5">
                <span className="font-mono-ui text-[11px] tracking-[0.1em] text-[#7c756c]">{group.day}</span>
                <span className="h-px flex-1 bg-[var(--line)]" />
                <span className="font-mono-ui text-[11px] text-[var(--nav-label)]">{group.entries.length} evento{group.entries.length === 1 ? '' : 's'}</span>
              </div>
              {group.entries.map((entry) => {
                const from = entry.from_status && ['open', 'acknowledged', 'resolved', 'dismissed'].includes(entry.from_status) ? (entry.from_status as IncidentStatus) : null
                const to = entry.to_status && ['open', 'acknowledged', 'resolved', 'dismissed'].includes(entry.to_status) ? (entry.to_status as IncidentStatus) : null
                const statusChip = (status: IncidentStatus) => ({ open: { label: 'Aberto', bg: '#F6E4DC', color: '#B14A22' }, acknowledged: { label: 'Reconhecido', bg: '#F3E9D6', color: '#946416' }, resolved: { label: 'Resolvido', bg: '#E4EFE9', color: '#1F6B4A' }, dismissed: { label: 'Descartado', bg: '#EEEAE3', color: '#7C756C' } }[status])
                return (
                  <div key={entry.id} className="grid grid-cols-[88px_1.5fr_1.2fr_0.9fr_1.3fr] items-center gap-3 border-b border-[color:var(--row)] px-[18px] py-3 last:border-b-0">
                    <span className="font-mono-ui text-xs text-[var(--muted)]">{hms(entry.created_at)}</span>
                    <span className="flex items-center gap-2.5">
                      <span className="h-[7px] w-[7px] flex-none rounded-full" style={{ background: auditActionDot(entry.action) }} />
                      <span className="truncate text-[13px] text-[var(--ink)]">{auditActionLabel(entry.action)}</span>
                    </span>
                    <span className="truncate text-[13px] text-[var(--muted)]">{entry.actor}</span>
                    <button type="button" onClick={() => openWorkspaceSection('incidents')} className="justify-self-start truncate font-mono-ui text-xs text-[var(--accent)] hover:underline">{entry.incident_id.slice(0, 10)}</button>
                    <span className="flex items-center gap-1.5">
                      {from ? <span className="rounded-[5px] px-1.5 py-0.5 text-[10px] font-semibold" style={{ background: statusChip(from).bg, color: statusChip(from).color }}>{statusChip(from).label}</span> : <span className="text-[11px] text-[var(--nav-label)]">—</span>}
                      <Icon name="arrow-right" size={11} className="text-[var(--nav-label)]" />
                      {to ? <span className="rounded-[5px] px-1.5 py-0.5 text-[10px] font-semibold" style={{ background: statusChip(to).bg, color: statusChip(to).color }}>{statusChip(to).label}</span> : null}
                    </span>
                  </div>
                )
              })}
            </div>
          ))}
        </TableShell>
      ) : (
        <div className="rounded-xl border border-dashed border-[color:var(--line)] bg-[var(--card)] px-5 py-8">
          <p className="font-display text-lg font-bold text-[var(--ink)]">Selecione um incidente para ver a trilha</p>
          <p className="mt-2 max-w-xl text-sm leading-7 text-[var(--muted)]">Hoje a auditoria vem por incidente. Abra um incidente em <button type="button" onClick={() => openWorkspaceSection('incidents')} className="font-medium text-[var(--accent)] hover:underline">Incidentes</button> para carregar seu histórico de ações.</p>
        </div>
      )}

      <div className="mt-3.5 flex items-center gap-2.5 rounded-[9px] border border-dashed border-[color:var(--line)] px-4 py-3">
        <Icon name="file-text" size={16} className="flex-none text-[var(--muted-2)]" />
        <p className="text-[13px] text-[var(--muted-2)]">Hoje a trilha vem por incidente. <span className="font-semibold text-[var(--muted)]">Em breve:</span> visão global por usuário/site/janela, filtros por tipo de ação e exportação CSV/PDF.</p>
      </div>
    </div>
  )
}
