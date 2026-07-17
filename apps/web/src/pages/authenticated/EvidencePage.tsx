import type { ReactNode } from 'react'
import type { Incident } from '../../api/incidents'
import { Button, PageHeader } from '../../components/ui/dashboard'
import { Icon } from '../../components/ui/icons'

function severityMeta(severity: string) {
  const meta: Record<string, { label: string; dot: string; soft: string; text: string }> = {
    high: { label: 'Alta', dot: '#C1552B', soft: '#F6E4DC', text: '#B14A22' },
    medium: { label: 'Média', dot: '#C98A2B', soft: '#F3E9D6', text: '#946416' },
    low: { label: 'Baixa', dot: '#2F7D57', soft: '#E4EFE9', text: '#1F6B4A' },
  }
  return meta[severity.toLowerCase()] ?? { label: severity, dot: '#8E887B', soft: '#EEEAE3', text: '#7C756C' }
}

export function EvidencePage({
  selectedIncident,
  openWorkspaceSection,
  evidenceExplorer,
}: {
  selectedIncident: Incident | null
  openWorkspaceSection: (section: 'incidents') => void
  evidenceExplorer: ReactNode
}) {
  const sev = selectedIncident ? severityMeta(selectedIncident.severity) : null

  return (
    <div className="mx-auto max-w-[1200px]">
      <PageHeader
        eyebrow="CONTEXTO DE INCIDENTE"
        title="Evidências do incidente"
        description="Conteúdo privado e auditável. Ao abrir uma evidência, o sistema prepara um acesso seguro temporário e registra a ação no log de auditoria com autor, data e finalidade."
        actions={selectedIncident ? <Button variant="secondary" onClick={() => openWorkspaceSection('incidents')}><Icon name="arrow-left" size={15} className="text-[var(--muted-2)]" /> Abrir no Incidentes</Button> : undefined}
      />

      {selectedIncident && sev ? (
        <div className="mb-3.5 flex flex-wrap items-center gap-2.5">
          <span className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-[3px] text-[12px] font-medium" style={{ background: sev.soft, color: sev.text }}>
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: sev.dot }} />
            {selectedIncident.summary}
          </span>
          <span className="font-mono-ui text-[12px] text-[var(--label)]">{selectedIncident.id.slice(0, 12)} · {selectedIncident.site_id ?? 'Site —'} · {selectedIncident.camera_id}</span>
        </div>
      ) : null}

      <div className="mb-4 flex items-center gap-3 rounded-[10px] border border-[#E3D8C8] bg-[#F7F0E2] px-4 py-3">
        <Icon name="lock" size={18} className="flex-none text-[#946416]" />
        <p className="flex-1 text-[13px] leading-[1.5] text-[#5a4a2a]"><span className="font-semibold text-[#3f3212]">Conteúdo privado e auditável.</span> Ao abrir uma evidência, o sistema prepara um acesso seguro temporário e registra a ação no log de auditoria com autor, data e finalidade.</p>
        <span className="hidden flex-none font-mono-ui text-[11px] text-[#946416] sm:block">RLS · LGPD</span>
      </div>

      {selectedIncident ? evidenceExplorer : <div className="rounded-xl border border-dashed border-[color:var(--line)] bg-[var(--card)] p-8 text-sm leading-7 text-[var(--muted)]">Selecione um incidente na aba <span className="font-medium text-[var(--ink)]">Incidentes</span> para abrir a evidência correspondente.</div>}
    </div>
  )
}
