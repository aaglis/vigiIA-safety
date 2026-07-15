import type { IncidentStatus } from '../../api/incidents'
import type { OperationEntityStatus, OperationZoneType } from '../../api/operations'

export function MonogramMark({ className = '', variant = 'default' }: { className?: string; variant?: 'default' | 'reverse' }) {
  const outline = variant === 'reverse' ? '#F5F3EF' : '#201B18'
  const inner = variant === 'reverse' ? '#E07A4E' : '#C1552B'
  return (
    <svg viewBox="0 0 120 120" className={className} aria-hidden="true">
      <rect x="10" y="10" width="100" height="100" rx="28" fill="none" stroke={outline} strokeWidth="9" />
      <rect x="42" y="42" width="36" height="36" rx="7" fill={inner} />
    </svg>
  )
}

export function Logo({ markClassName = 'h-9 w-9', size = 'md', variant = 'default' }: { markClassName?: string; size?: 'sm' | 'md' | 'lg'; variant?: 'default' | 'reverse' }) {
  const vigiaSize = size === 'lg' ? 'text-2xl' : size === 'sm' ? 'text-[15px]' : 'text-lg'
  const safetySize = size === 'lg' ? 'text-[11px]' : 'text-[8px]'
  const vigiaColor = variant === 'reverse' ? 'text-[var(--paper)]' : 'text-[var(--ink)]'
  return (
    <span className="flex items-center gap-2.5">
      <MonogramMark className={markClassName} variant={variant} />
      <span className="flex flex-col leading-none">
        <span className={`font-semibold tracking-[0.03em] ${vigiaSize} ${vigiaColor}`}>VIGIA</span>
        <span className={`mt-1 font-mono-ui uppercase tracking-[0.34em] text-[var(--label)] ${safetySize}`}>SAFETY</span>
      </span>
    </span>
  )
}

export function SectionHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <div className="max-w-2xl">
      <p className="font-mono-ui text-[11px] uppercase tracking-[0.32em] text-[var(--accent)]">{eyebrow}</p>
      <h2 className="mt-3 font-display text-3xl leading-tight text-[var(--ink)] md:text-4xl">{title}</h2>
      <p className="mt-4 max-w-xl text-sm leading-7 text-[var(--muted)] md:text-base">{description}</p>
    </div>
  )
}

export function StatusPill({ status }: { status: IncidentStatus }) {
  const styles: Record<IncidentStatus, string> = {
    open: 'bg-[rgba(201,138,43,0.16)] text-[#7a5314] border-[rgba(201,138,43,0.25)]',
    acknowledged: 'bg-[rgba(47,125,87,0.14)] text-[#236444] border-[rgba(47,125,87,0.22)]',
    resolved: 'bg-[rgba(32,27,24,0.9)] text-[var(--paper)] border-[rgba(32,27,24,0.8)]',
    dismissed: 'bg-[rgba(193,85,43,0.16)] text-[#9e4120] border-[rgba(193,85,43,0.28)]',
  }
  const labels: Record<IncidentStatus, string> = { open: 'Aberto', acknowledged: 'Reconhecido', resolved: 'Resolvido', dismissed: 'Descartado' }
  return <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-medium ${styles[status]}`}>{labels[status]}</span>
}

export function SeverityPill({ severity }: { severity: string }) {
  const normalized = severity.toLowerCase()
  const tone = normalized === 'high' ? 'bg-[rgba(193,85,43,0.16)] text-[#8f3c1c]' : normalized === 'medium' ? 'bg-[rgba(201,138,43,0.18)] text-[#7a5314]' : 'bg-[rgba(47,125,87,0.14)] text-[#236444]'
  return <span className={`inline-flex rounded-full border border-black/5 px-3 py-1 text-xs font-medium capitalize ${tone}`}>{severity}</span>
}

export function OperationStatusPill({ status }: { status: OperationEntityStatus }) {
  const styles: Record<OperationEntityStatus, string> = {
    active: 'bg-[rgba(47,125,87,0.14)] text-[#236444] border-[rgba(47,125,87,0.22)]',
    inactive: 'bg-[rgba(201,138,43,0.16)] text-[#7a5314] border-[rgba(201,138,43,0.25)]',
    suspended: 'bg-[rgba(193,85,43,0.16)] text-[#9e4120] border-[rgba(193,85,43,0.28)]',
  }
  const labels: Record<OperationEntityStatus, string> = { active: 'Ativo', inactive: 'Inativo', suspended: 'Suspenso' }
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.18em] ${styles[status]}`}>{labels[status]}</span>
}

export function ZoneTypePill({ zoneType }: { zoneType: OperationZoneType }) {
  const styles: Record<OperationZoneType, string> = {
    access: 'bg-[rgba(32,27,24,0.9)] text-[var(--paper)] border-[rgba(32,27,24,0.8)]',
    restricted: 'bg-[rgba(193,85,43,0.16)] text-[#9e4120] border-[rgba(193,85,43,0.28)]',
    ppe: 'bg-[rgba(201,138,43,0.16)] text-[#7a5314] border-[rgba(201,138,43,0.25)]',
  }
  const labels: Record<OperationZoneType, string> = { access: 'Acesso', restricted: 'Restrita', ppe: 'EPI' }
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.18em] ${styles[zoneType]}`}>{labels[zoneType]}</span>
}
