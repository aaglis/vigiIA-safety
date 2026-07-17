import { forwardRef, useEffect, useId, useRef, useState, type ButtonHTMLAttributes, type ForwardedRef, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from 'react'

type BadgeTone = 'neutral' | 'good' | 'warning' | 'critical' | 'dark'

type PageStateProps = {
  title: string
  description: string
  action?: ReactNode
  eyebrow?: string
  icon?: ReactNode
}

type FieldBaseProps = {
  label: string
  helperText?: string
  errorText?: string
}

export type AsyncSelectOption = {
  value: string
  label: string
  description?: string
}

export type AsyncSelectPageResult<T extends AsyncSelectOption> = {
  items: T[]
  hasMore: boolean
}

export type AsyncSelectLoadPage<T extends AsyncSelectOption> = (args: {
  query: string
  page: number
  signal: AbortSignal
}) => Promise<AsyncSelectPageResult<T>>

const baseButton = 'inline-flex items-center justify-center gap-2 rounded-[10px] border px-4 py-2 text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(193,85,43,0.18)] disabled:cursor-not-allowed disabled:opacity-60'

export const Button = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; size?: 'sm' | 'md' | 'lg' }>(function Button(
  { variant = 'primary', size = 'md', className = '', type = 'button', ...props },
  ref: ForwardedRef<HTMLButtonElement>,
) {
  const variantClass = variant === 'primary'
    ? 'border-[var(--accent)] bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)]'
    : variant === 'secondary'
      ? 'border-[color:var(--line)] bg-[var(--paper)] text-[var(--ink)] hover:bg-white'
      : variant === 'danger'
        ? 'border-[rgba(193,85,43,0.18)] bg-[rgba(193,85,43,0.08)] text-[#9e4120] hover:bg-[rgba(193,85,43,0.12)]'
        : 'border-transparent bg-transparent text-[var(--ink)] hover:bg-[rgba(255,255,255,0.65)]'
  const sizeClass = size === 'sm' ? 'h-9 px-3 text-xs' : size === 'lg' ? 'h-12 px-5 text-sm' : 'h-10 px-4 text-sm'
  return <button ref={ref} type={type} className={`${baseButton} ${sizeClass} ${variantClass} ${className}`} {...props} />
})

export function Modal({
  open,
  title,
  description,
  onClose,
  children,
  className = '',
}: {
  open: boolean
  title: string
  description?: string
  onClose: () => void
  children: ReactNode
  className?: string
}) {
  const titleId = useId()
  const descriptionId = useId()
  const closeRef = useRef<HTMLButtonElement | null>(null)

  // Foco inicial depende SÓ de `open`. Se depender de `onClose` (que costuma ser arrow
  // inline, nova a cada render), cada tecla digitada re-roda o effect e rouba o foco do
  // campo para o botão Fechar — só a primeira letra entrava.
  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
  }, [open])

  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose, open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-[rgba(32,27,24,0.42)] px-4 py-4 backdrop-blur-sm sm:items-center" role="presentation">
      <button type="button" aria-label="Fechar modal" onClick={onClose} className="absolute inset-0 cursor-default" />
      {/* max-h + flex-col: o modal nunca passa da viewport. O cabeçalho fica parado e só
          o corpo rola — sem isto, conteúdo longo empurra os botões para fora da tela. */}
      <div
        className={`relative z-10 flex max-h-[calc(100dvh-2rem)] w-full max-w-2xl flex-col overflow-hidden rounded-[28px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.98)] shadow-[0_30px_90px_rgba(32,27,24,0.22)] ${className}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
      >
        <div className="flex flex-none items-start justify-between gap-4 border-b border-[color:var(--line)] px-6 py-5">
          <div>
            <p id={titleId} className="font-mono-ui text-[11px] uppercase tracking-[0.3em] text-[var(--accent)]">{title}</p>
            {description ? <p id={descriptionId} className="mt-2 max-w-xl text-sm leading-6 text-[var(--muted)]">{description}</p> : null}
          </div>
          <Button ref={closeRef} variant="secondary" size="sm" onClick={onClose}>Fechar</Button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-6 py-6">{children}</div>
      </div>
    </div>
  )
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className = '',
}: {
  eyebrow?: string
  title: string
  description?: string
  actions?: ReactNode
  className?: string
}) {
  return (
    <div className={`mb-5 flex flex-wrap items-start justify-between gap-4 ${className}`}>
      <div className="min-w-0">
        {eyebrow ? <p className="font-mono-ui text-[11px] uppercase tracking-[0.3em] text-[var(--accent)]">{eyebrow}</p> : null}
        <h2 className="mt-2 font-display text-[26px] font-bold leading-none tracking-[-0.025em] text-[var(--ink)]">{title}</h2>
        {description ? <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2.5">{actions}</div> : null}
    </div>
  )
}

export function TableShell({
  title,
  description,
  actions,
  children,
  className = '',
}: {
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`overflow-hidden rounded-xl border border-[color:var(--border)] bg-[var(--card)] ${className}`}>
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[color:var(--divider)] px-[18px] py-[15px]">
        <div className="min-w-0">
          <h3 className="font-display text-[15px] font-bold text-[var(--ink)]">{title}</h3>
          {description ? <p className="mt-1 max-w-2xl text-xs leading-5 text-[var(--muted)]">{description}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
      <div>{children}</div>
    </section>
  )
}

// forwardRef é obrigatório: o `register()` do react-hook-form entrega um `ref`, e no
// React 18 ref NÃO passa por {...props}. Sem isto o RHF nunca enxerga o input — o valor
// chega undefined e a validação falha com "Invalid input" em vez da mensagem do campo.
export const TextField = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & FieldBaseProps>(function TextField(
  { label, helperText, errorText, className = '', ...props },
  ref,
) {
  const id = useId()
  const helperId = `${id}-help`
  const errorId = `${id}-error`
  const describedBy = errorText ? errorId : helperText ? helperId : undefined

  return (
    <label className="block space-y-2" htmlFor={id}>
      <span className="text-[13px] font-medium text-[#403933]">{label}</span>
      <input
        id={id}
        ref={ref}
        aria-invalid={Boolean(errorText)}
        aria-describedby={describedBy}
        {...props}
        className={`h-12 w-full rounded-[10px] border border-[#dcd7cc] bg-[var(--card)] px-3.5 text-[15px] text-[var(--ink)] outline-none transition placeholder:text-[#a09a8e] focus:border-[var(--accent)] focus:ring-2 focus:ring-[rgba(193,85,43,0.16)] focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60 ${errorText ? 'border-[rgba(193,85,43,0.35)] focus:border-[rgba(193,85,43,0.8)] focus:ring-[rgba(193,85,43,0.18)]' : ''} ${className}`}
      />
      {errorText ? <p id={errorId} className="text-[12px] leading-5 text-[#9e4120]">{errorText}</p> : helperText ? <p id={helperId} className="text-[12px] leading-5 text-[var(--label)]">{helperText}</p> : null}
    </label>
  )
})

export const SelectField = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement> & FieldBaseProps & { children: ReactNode }>(function SelectField(
  { label, helperText, errorText, className = '', children, ...props },
  ref,
) {
  const id = useId()
  const helperId = `${id}-help`
  const errorId = `${id}-error`
  const describedBy = errorText ? errorId : helperText ? helperId : undefined

  return (
    <label className="block space-y-2" htmlFor={id}>
      <span className="text-[13px] font-medium text-[#403933]">{label}</span>
      <select
        id={id}
        ref={ref}
        aria-invalid={Boolean(errorText)}
        aria-describedby={describedBy}
        {...props}
        className={`h-12 w-full rounded-[10px] border border-[#dcd7cc] bg-[var(--card)] px-3.5 text-[15px] text-[var(--ink)] outline-none transition focus:border-[var(--accent)] focus:ring-2 focus:ring-[rgba(193,85,43,0.16)] focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60 ${errorText ? 'border-[rgba(193,85,43,0.35)] focus:border-[rgba(193,85,43,0.8)] focus:ring-[rgba(193,85,43,0.18)]' : ''} ${className}`}
      >
        {children}
      </select>
      {errorText ? <p id={errorId} className="text-[12px] leading-5 text-[#9e4120]">{errorText}</p> : helperText ? <p id={helperId} className="text-[12px] leading-5 text-[var(--label)]">{helperText}</p> : null}
    </label>
  )
})

function toneClasses(tone: BadgeTone) {
  if (tone === 'good') return 'bg-[rgba(47,125,87,0.14)] text-[#236444] border-[rgba(47,125,87,0.22)]'
  if (tone === 'warning') return 'bg-[rgba(201,138,43,0.16)] text-[#7a5314] border-[rgba(201,138,43,0.25)]'
  if (tone === 'critical') return 'bg-[rgba(193,85,43,0.16)] text-[#9e4120] border-[rgba(193,85,43,0.28)]'
  if (tone === 'dark') return 'bg-[rgba(32,27,24,0.9)] text-[var(--paper)] border-[rgba(32,27,24,0.8)]'
  return 'bg-[rgba(32,27,24,0.08)] text-[var(--muted)] border-[color:var(--line)]'
}

export function StatusBadge({ label, tone = 'neutral', className = '' }: { label: string; tone?: BadgeTone; className?: string }) {
  return <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-medium ${toneClasses(tone)} ${className}`}>{label}</span>
}

export function SeverityBadge({ severity, className = '' }: { severity: string; className?: string }) {
  const normalized = severity.toLowerCase()
  const tone = normalized === 'high' ? 'critical' : normalized === 'medium' ? 'warning' : 'good'
  return <StatusBadge label={severity} tone={tone} className={className} />
}

function StateFrame({
  title,
  description,
  icon,
  action,
  className = '',
}: PageStateProps & { className?: string }) {
  return (
    <div className={`rounded-[28px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.66)] p-6 shadow-[0_16px_40px_rgba(32,27,24,0.06)] ${className}`}>
      <div className="flex items-start gap-4">
        {icon ? <div className="mt-1 rounded-[14px] border border-[color:var(--line)] bg-[var(--paper)] p-3 text-[var(--accent)]">{icon}</div> : null}
        <div className="min-w-0 flex-1">
          <p className="font-display text-2xl text-[var(--ink)]">{title}</p>
          <p className="mt-2 max-w-2xl text-sm leading-7 text-[var(--muted)]">{description}</p>
          {action ? <div className="mt-4">{action}</div> : null}
        </div>
      </div>
    </div>
  )
}

export function PageState(props: PageStateProps & { className?: string }) {
  return <StateFrame {...props} />
}

export function EmptyState(props: PageStateProps & { className?: string }) {
  return <StateFrame {...props} />
}

export function ErrorState(props: PageStateProps & { className?: string }) {
  return <StateFrame {...props} className={`border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.08)] ${props.className ?? ''}`} />
}

export function PagePanel({
  eyebrow,
  title,
  description,
  actions,
  children,
  className = '',
}: {
  eyebrow?: string
  title?: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`rounded-[32px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.92)] p-6 shadow-[0_22px_60px_rgba(32,27,24,0.08)] ${className}`}>
      {(eyebrow || title || description || actions) ? (
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            {eyebrow ? <p className="font-mono-ui text-[11px] uppercase tracking-[0.3em] text-[var(--accent)]">{eyebrow}</p> : null}
            {title ? <h2 className="mt-3 font-display text-3xl leading-tight text-[var(--ink)]">{title}</h2> : null}
            {description ? <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--muted)]">{description}</p> : null}
          </div>
          {actions ? <div>{actions}</div> : null}
        </div>
      ) : null}
      <div className={eyebrow || title || description || actions ? 'mt-5' : ''}>{children}</div>
    </section>
  )
}

export function DataCard({
  label,
  value,
  detail,
  tone = 'neutral',
  className = '',
}: {
  label: string
  value: ReactNode
  detail?: string
  tone?: BadgeTone
  className?: string
}) {
  return (
    <article className={`rounded-[24px] border border-[color:var(--line)] bg-[rgba(255,255,255,0.66)] p-4 ${className}`}>
      <div className="flex items-start justify-between gap-3">
        <p className="font-mono-ui text-[11px] uppercase tracking-[0.28em] text-[var(--muted)]">{label}</p>
        {tone !== 'neutral' ? <StatusBadge label={tone === 'good' ? 'OK' : tone === 'warning' ? 'Atenção' : tone === 'critical' ? 'Crítico' : '—'} tone={tone} /> : null}
      </div>
      <div className="mt-3 font-display text-3xl text-[var(--ink)]">{value}</div>
      {detail ? <p className="mt-2 text-xs uppercase tracking-[0.22em] text-[var(--muted)]">{detail}</p> : null}
    </article>
  )
}

export function AsyncPaginatedSelect<T extends AsyncSelectOption>({
  label,
  value,
  onChange,
  loadPage,
  helperText,
  errorText,
  disabled,
  placeholder = 'Selecionar…',
  searchPlaceholder = 'Pesquisar…',
  emptyLabel = 'Nenhuma opção encontrada.',
  loadingLabel = 'Carregando…',
  renderOption,
}: {
  label: string
  value: string | null
  onChange: (value: string | null, option: T | null) => void
  loadPage: AsyncSelectLoadPage<T>
  helperText?: string
  errorText?: string
  disabled?: boolean
  placeholder?: string
  searchPlaceholder?: string
  emptyLabel?: string
  loadingLabel?: string
  renderOption?: (option: T) => ReactNode
}) {
  const id = useId()
  const panelId = `${id}-panel`
  const searchId = `${id}-search`
  const listRef = useRef<HTMLDivElement | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [options, setOptions] = useState<T[]>([])
  const [page, setPage] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [selectedOption, setSelectedOption] = useState<T | null>(null)

  const selectedLabel = selectedOption?.label ?? placeholder

  const mergeOptions = (incoming: T[]) => {
    setOptions((current) => {
      const map = new Map<string, T>()
      for (const option of current) map.set(option.value, option)
      for (const option of incoming) map.set(option.value, option)
      return Array.from(map.values())
    })
  }

  const fetchPage = async (nextPage: number, nextQuery = query) => {
    if (loading || (!hasMore && nextPage !== 1)) return
    setLoading(true)
    setLoadError(null)
    const controller = new AbortController()
    try {
      const result = await loadPage({ query: nextQuery, page: nextPage, signal: controller.signal })
      if (nextPage === 1) {
        setOptions(result.items)
      } else {
        mergeOptions(result.items)
      }
      setPage(nextPage)
      setHasMore(result.hasMore)
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Não foi possível carregar opções.')
    } finally {
      setLoading(false)
    }
    return () => controller.abort()
  }

  useEffect(() => {
    if (!open) return
    setPage(0)
    setHasMore(true)
    setOptions([])
    setLoadError(null)
    setQuery('')
    void fetchPage(1, '')
  }, [open])

  useEffect(() => {
    if (!open) return
    if (page === 0) return
    const timeout = window.setTimeout(() => {
      setPage(0)
      setHasMore(true)
      setOptions([])
      void fetchPage(1, query)
    }, 250)
    return () => window.clearTimeout(timeout)
  }, [query])

  useEffect(() => {
    if (!open) return
    inputRef.current?.focus()
  }, [open])

  useEffect(() => {
    if (!value) {
      setSelectedOption(null)
      return
    }
    const existing = options.find((option) => option.value === value)
    if (existing) setSelectedOption(existing)
  }, [options, value])

  useEffect(() => {
    if (!open) return
    const el = listRef.current
    if (!el) return
    const onScroll = () => {
      if (loading || !hasMore) return
      const threshold = 48
      const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - threshold
      if (nearBottom) void fetchPage(page + 1, query)
    }
    el.addEventListener('scroll', onScroll, { passive: true })
    return () => el.removeEventListener('scroll', onScroll)
  }, [hasMore, loading, open, page, query])

  const close = () => setOpen(false)

  return (
    <div className="block space-y-2">
      <span className="text-[13px] font-medium text-[#403933]">{label}</span>
      <button
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((current) => !current)}
        className={`flex h-12 w-full items-center justify-between rounded-[10px] border border-[#dcd7cc] bg-[var(--card)] px-3.5 text-left text-[15px] text-[var(--ink)] outline-none transition hover:border-[var(--accent)] focus-visible:border-[var(--accent)] focus-visible:ring-2 focus-visible:ring-[rgba(193,85,43,0.16)] disabled:cursor-not-allowed disabled:opacity-60 ${errorText ? 'border-[rgba(193,85,43,0.35)]' : ''}`}
      >
        <span className={selectedOption ? '' : 'text-[#a09a8e]'}>{selectedLabel}</span>
        <span className="text-[10px] uppercase tracking-[0.22em] text-[var(--label)]">Selecionar</span>
      </button>
      {errorText ? <p className="text-[12px] leading-5 text-[#9e4120]">{errorText}</p> : helperText ? <p className="text-[12px] leading-5 text-[var(--label)]">{helperText}</p> : null}

      {open ? (
        <div className="relative z-40">
          <div className="fixed inset-0 z-30" aria-hidden="true" onClick={close} />
          <div id={panelId} className="absolute z-40 mt-2 w-full overflow-hidden rounded-[20px] border border-[color:var(--line)] bg-[rgba(245,243,239,0.98)] shadow-[0_26px_80px_rgba(32,27,24,0.18)]">
            <div className="border-b border-[color:var(--line)] p-3">
              <input
                ref={inputRef}
                id={searchId}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={searchPlaceholder}
                className="h-11 w-full rounded-[10px] border border-[#dcd7cc] bg-[var(--card)] px-3.5 text-sm text-[var(--ink)] outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[rgba(193,85,43,0.16)]"
              />
            </div>
            <div ref={listRef} role="listbox" aria-labelledby={id} className="max-h-72 overflow-y-auto p-2">
              {loading && options.length === 0 ? (
                <div className="px-3 py-4 text-sm text-[var(--muted)]">{loadingLabel}</div>
              ) : loadError ? (
                <div className="rounded-[14px] border border-[rgba(193,85,43,0.2)] bg-[rgba(193,85,43,0.08)] px-3 py-3 text-sm text-[#9e4120]">{loadError}</div>
              ) : options.length === 0 ? (
                <div className="px-3 py-4 text-sm text-[var(--muted)]">{emptyLabel}</div>
              ) : (
                options.map((option) => {
                  const active = option.value === value
                  return (
                    <button
                      key={option.value}
                      type="button"
                      role="option"
                      aria-selected={active}
                      onClick={() => {
                        setSelectedOption(option)
                        onChange(option.value, option)
                        close()
                      }}
                      className={`mb-1 flex w-full items-start gap-3 rounded-[14px] border px-3 py-3 text-left transition last:mb-0 hover:bg-[rgba(193,85,43,0.05)] ${active ? 'border-[rgba(193,85,43,0.26)] bg-[rgba(193,85,43,0.08)]' : 'border-transparent bg-transparent'}`}
                    >
                      <span className={`mt-1 h-2.5 w-2.5 rounded-full ${active ? 'bg-[var(--accent)]' : 'bg-[var(--line)]'}`} />
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm font-medium text-[var(--ink)]">{renderOption ? renderOption(option) : option.label}</span>
                        {option.description ? <span className="mt-1 block text-xs leading-5 text-[var(--muted)]">{option.description}</span> : null}
                      </span>
                    </button>
                  )
                })
              )}
              {loading && options.length > 0 ? <div className="px-3 py-3 text-xs uppercase tracking-[0.24em] text-[var(--label)]">Carregando mais…</div> : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
