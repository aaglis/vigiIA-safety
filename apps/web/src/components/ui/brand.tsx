import type { ReactNode, InputHTMLAttributes, SelectHTMLAttributes } from 'react'
import type { IncidentStatus } from '../../api/incidents'
import type { OperationEntityStatus, OperationZoneType } from '../../api/operations'
export { AsyncPaginatedSelect, Button, DataCard, EmptyState, ErrorState, PagePanel, PageState, StatusBadge, SeverityBadge } from './dashboard'

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

export function Modal({
  open,
  title,
  description,
  onClose,
  children,
}: {
  open: boolean
  title: string
  description?: string
  onClose: () => void
  children: ReactNode
}) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-[rgba(32,27,24,0.42)] px-4 py-4 backdrop-blur-sm sm:items-center">
      <button type="button" aria-label="Fechar modal" onClick={onClose} className="absolute inset-0 cursor-default" />
      {/* max-h + flex-col: o modal nunca passa da viewport. O cabeçalho fica parado e só
          o corpo rola — sem isto, conteúdo longo empurra os botões para fora da tela. */}
      <div role="dialog" aria-modal="true" aria-label={title} className="relative z-10 flex max-h-[calc(100dvh-2rem)] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-[color:var(--line)] bg-[rgba(245,243,239,0.98)] shadow-[0_30px_90px_rgba(32,27,24,0.22)]">
        <div className="flex flex-none items-start justify-between gap-4 border-b border-[color:var(--line)] px-6 py-5">
          <div>
            <p className="font-mono-ui text-[11px] uppercase tracking-[0.3em] text-[var(--accent)]">{title}</p>
            {description ? <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--muted)]">{description}</p> : null}
          </div>
          <button type="button" onClick={onClose} className="rounded-lg border border-[color:var(--line)] bg-[var(--paper)] px-3 py-2 text-xs uppercase tracking-[0.2em] text-[var(--muted)] transition hover:bg-white">Fechar</button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-6 py-6">{children}</div>
      </div>
    </div>
  )
}

export function TextField({ label, helperText, errorText, className = '', ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; helperText?: string; errorText?: string }) {
  return (
    <label className="block space-y-2">
      <span className="text-[13px] font-medium text-[#403933]">{label}</span>
      <input
        {...props}
        className={`h-12 w-full rounded-[10px] border border-[#dcd7cc] bg-[var(--card)] px-3.5 text-[15px] text-[var(--ink)] outline-none transition placeholder:text-[#a09a8e] focus:border-[var(--accent)] focus:ring-2 focus:ring-[rgba(193,85,43,0.16)] disabled:cursor-not-allowed disabled:opacity-60 ${errorText ? 'border-[rgba(193,85,43,0.35)] focus:border-[rgba(193,85,43,0.8)] focus:ring-[rgba(193,85,43,0.18)]' : ''} ${className}`}
      />
      {errorText ? <p className="text-[12px] leading-5 text-[#9e4120]">{errorText}</p> : helperText ? <p className="text-[12px] leading-5 text-[var(--label)]">{helperText}</p> : null}
    </label>
  )
}

export function SelectField({ label, helperText, errorText, className = '', children, ...props }: SelectHTMLAttributes<HTMLSelectElement> & { label: string; helperText?: string; errorText?: string; children: ReactNode }) {
  return (
    <label className="block space-y-2">
      <span className="text-[13px] font-medium text-[#403933]">{label}</span>
      <select
        {...props}
        className={`h-12 w-full rounded-[10px] border border-[#dcd7cc] bg-[var(--card)] px-3.5 text-[15px] text-[var(--ink)] outline-none transition focus:border-[var(--accent)] focus:ring-2 focus:ring-[rgba(193,85,43,0.16)] disabled:cursor-not-allowed disabled:opacity-60 ${errorText ? 'border-[rgba(193,85,43,0.35)] focus:border-[rgba(193,85,43,0.8)] focus:ring-[rgba(193,85,43,0.18)]' : ''} ${className}`}
      >
        {children}
      </select>
      {errorText ? <p className="text-[12px] leading-5 text-[#9e4120]">{errorText}</p> : helperText ? <p className="text-[12px] leading-5 text-[var(--label)]">{helperText}</p> : null}
    </label>
  )
}

export function FormActions({
  primaryLabel,
  secondaryLabel,
  onPrimary,
  onSecondary,
  primaryDisabled,
  primaryHint,
}: {
  primaryLabel: string
  secondaryLabel: string
  onPrimary?: () => void
  onSecondary: () => void
  primaryDisabled?: boolean
  primaryHint?: string
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-xs leading-5 text-[var(--label)]">{primaryHint ?? 'Esta ação ainda depende da API de escrita.'}</p>
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={onSecondary} className="rounded-[9px] border border-[color:var(--line)] bg-[var(--paper)] px-5 py-3 text-sm font-medium text-[var(--ink)] transition hover:bg-white">
          {secondaryLabel}
        </button>
        <button type="button" onClick={onPrimary} disabled={primaryDisabled ?? true} className="rounded-[9px] bg-[var(--accent)] px-5 py-3 text-sm font-medium text-[var(--paper)] transition disabled:cursor-not-allowed disabled:opacity-60">
          {primaryLabel}
        </button>
      </div>
    </div>
  )
}
