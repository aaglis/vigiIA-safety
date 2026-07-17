import { useEffect, useMemo, useState } from 'react'
import type { Membership } from '../../api/auth'
import { Button, DataCard, FormActions, StatusBadge, TextField } from '../../components/ui/brand'
import { Icon } from '../../components/ui/icons'
import { usePlatformAdminMutations, usePlatformOrganizations } from '../../queries/platform'

type OrganizationMembership = Membership & { organization: Membership['organization'] & { slug?: string } }

function sessionBadge(active: boolean, isSession: boolean) {
  if (isSession) return { label: 'ATIVA NA SESSÃO', bg: '#F4E7DF', color: '#B14A22' }
  if (active) return { label: 'ATIVA', bg: '#E4EFE9', color: '#1F6B4A' }
  return { label: 'INATIVA', bg: '#F3E9D6', color: '#946416' }
}

export function OrganizationsPage({
  memberships,
  activeOrganizationId,
  platformRole,
  isLoading,
}: {
  memberships: Membership[]
  activeOrganizationId: string | null
  activeOrganizationName: string
  userName: string
  liveLabel: string
  platformRole?: string | null
  isLoading: boolean
}) {
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all')
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [selectedOrganizationId, setSelectedOrganizationId] = useState<string | null>(activeOrganizationId)
  const [createOpen, setCreateOpen] = useState(false)
  const [createName, setCreateName] = useState('')
  const [createLegalName, setCreateLegalName] = useState('')
  const [createTaxId, setCreateTaxId] = useState('')
  const [createPlan, setCreatePlan] = useState('')
  const [createLeaderEmail, setCreateLeaderEmail] = useState('')
  const [createError, setCreateError] = useState<string | null>(null)
  const [createFeedback, setCreateFeedback] = useState<string | null>(null)
  const [confirmAction, setConfirmAction] = useState<{ kind: 'suspend' | 'reactivate'; id: string; label: string } | null>(null)
  const [confirmText, setConfirmText] = useState('')
  const [confirmError, setConfirmError] = useState<string | null>(null)
  const [confirmFeedback, setConfirmFeedback] = useState<string | null>(null)

  const orgs = useMemo(() => memberships as OrganizationMembership[], [memberships])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return orgs.filter((membership) => {
      const org = membership.organization
      const slug = org.slug ?? org.id
      const matchesQuery = !q || org.name.toLowerCase().includes(q) || org.id.toLowerCase().includes(q) || slug.toLowerCase().includes(q) || membership.role.toLowerCase().includes(q)
      const matchesStatus = statusFilter === 'all' || (statusFilter === 'active' && membership.active) || (statusFilter === 'inactive' && !membership.active)
      const matchesRole = roleFilter === 'all' || membership.role.toLowerCase() === roleFilter
      return matchesQuery && matchesStatus && matchesRole
    })
  }, [orgs, query, roleFilter, statusFilter])

  useEffect(() => {
    if (selectedOrganizationId && filtered.some((m: OrganizationMembership) => m.organization.id === selectedOrganizationId)) return
    setSelectedOrganizationId(filtered[0]?.organization.id ?? orgs[0]?.organization.id ?? null)
  }, [filtered, orgs, selectedOrganizationId])

  const selected = orgs.find((m: OrganizationMembership) => m.organization.id === selectedOrganizationId) ?? filtered[0] ?? null
  const roleOptions = Array.from(new Set(orgs.map((m: OrganizationMembership) => m.role.toLowerCase()))).sort()
  const activeCount = orgs.filter((m: OrganizationMembership) => m.active).length
  const canReadPlatformOrganizations = platformRole === 'platform_admin'
  const platformOrgsQuery = usePlatformOrganizations(canReadPlatformOrganizations)
  const adminMutations = usePlatformAdminMutations()
  const canMutatePlatform = platformRole === 'platform_admin'

  useEffect(() => {
    if (!createOpen) return
    setCreateError(null); setCreateFeedback(null)
  }, [createOpen])

  return (
    <div className="mx-auto max-w-[1200px]">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-[26px] font-bold leading-none tracking-[-0.025em] text-[var(--ink)]">Tenants e vínculos</h2>
          <p className="mt-1.5 text-sm text-[var(--muted)]">Organizações às quais você tem acesso, seu papel e permissões em cada uma.</p>
        </div>
        <div className="flex items-center gap-2.5">
          {canMutatePlatform ? <Button type="button" variant="secondary" size="sm" onClick={() => setCreateOpen(true)}><Icon name="plus" size={15} /> Nova organização</Button> : <Button type="button" disabled title="Somente platform_admin" variant="secondary" size="sm">Editar seleção</Button>}
          {canMutatePlatform ? null : <Button type="button" disabled title="Somente platform_admin" size="sm" className="bg-[#E4C3B4] hover:bg-[#E4C3B4]"><Icon name="plus" size={15} /> Nova organização</Button>}
        </div>
      </div>

      <div className="mb-4 flex items-center gap-2.5 rounded-[9px] border border-[#E3D8C8] bg-[#F7F0E2] px-3.5 py-2.5">
        <Icon name="building" size={16} className="flex-none text-[#946416]" />
        <p className="text-[13px] leading-[1.4] text-[#5a4a2a]">A lista reflete seus <span className="font-semibold text-[#3f3212]">memberships</span> de <span className="font-mono-ui">/auth/me</span>. Mutação de plataforma só aparece para <span className="font-semibold text-[#3f3212]">platform_admin</span>.</p>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <DataCard label="Vínculos" value={orgs.length} />
        <DataCard label="Ativas" value={activeCount} tone="good" />
        <DataCard label="Filtradas" value={filtered.length} tone={filtered.length < orgs.length ? 'warning' : 'neutral'} />
      </div>

      <div className="mb-3.5 flex flex-wrap items-center gap-2">
        <div className="flex h-9 max-w-[320px] flex-1 items-center gap-2.5 rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-3">
          <Icon name="search" size={15} className="flex-none text-[var(--nav-label)]" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Nome, slug, id ou papel…" className="w-full bg-transparent text-[13px] text-[var(--ink)] outline-none placeholder:text-[var(--nav-label)]" />
        </div>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as 'all' | 'active' | 'inactive')} className="h-9 rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-2.5 text-[13px] text-[var(--muted)] outline-none focus:border-[rgba(193,85,43,0.5)]">
          <option value="all">Status: Todas</option>
          <option value="active">Ativas</option>
          <option value="inactive">Inativas</option>
        </select>
        <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="h-9 rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-2.5 text-[13px] text-[var(--muted)] outline-none focus:border-[rgba(193,85,43,0.5)]">
          <option value="all">Papel: Todos</option>
          {roleOptions.map((role) => <option key={role} value={role}>{role}</option>)}
        </select>
      </div>

      <div className="grid gap-3.5 xl:grid-cols-[minmax(0,1fr)_372px]">
        <div className="flex flex-col gap-2.5">
          {isLoading ? (
            <div className="rounded-[11px] border border-[color:var(--border)] bg-[var(--card)] px-4 py-6 text-sm text-[var(--muted)]">Carregando organizações…</div>
          ) : filtered.length === 0 ? (
            <div className="rounded-[11px] border border-dashed border-[color:var(--line)] bg-[var(--card)] px-4 py-6 text-sm leading-7 text-[var(--muted)]">Nenhuma organização corresponde aos filtros.</div>
          ) : filtered.map((membership) => {
            const org = membership.organization
            const isSession = org.id === activeOrganizationId
            const badge = sessionBadge(membership.active, isSession)
            const isSelected = org.id === selectedOrganizationId
            const slug = org.slug ?? org.id
            return (
              <button key={org.id} type="button" onClick={() => setSelectedOrganizationId(org.id)} className={`relative rounded-[11px] border px-4 py-3.5 text-left transition ${isSelected ? 'border-[#EAD8CD] bg-[#F9EEE7]' : 'border-[color:var(--border)] bg-[var(--card)] hover:bg-[rgba(32,27,24,0.02)]'} ${!membership.active ? 'opacity-75' : ''}`}>
                {isSelected ? <span className="absolute inset-y-3.5 left-0 w-[3px] rounded-full bg-[var(--accent)]" /> : null}
                <div className="mb-1.5 flex flex-wrap items-center gap-2.5">
                  <span className="text-[15px] font-semibold text-[var(--ink)]">{org.name}</span>
                  <StatusBadge label={badge.label} tone={isSession ? 'dark' : membership.active ? 'good' : 'warning'} className="rounded-[5px] px-2 py-0.5 text-[10px] font-semibold tracking-[0.05em]" />
                </div>
                <p className="mb-2.5 font-mono-ui text-[11px] text-[var(--muted-2)]">{slug} · {org.id}</p>
                <div className="flex flex-wrap gap-1.5">
                  <span className="rounded-full bg-[var(--divider)] px-2.5 py-0.5 text-[11px] text-[var(--muted)]">{membership.role}</span>
                  <span className="rounded-full bg-[var(--divider)] px-2.5 py-0.5 text-[11px] text-[var(--muted)]">{membership.permissions.length} {membership.permissions.length === 1 ? 'permissão' : 'permissões'}</span>
                </div>
              </button>
            )
          })}
        </div>

        <div className="flex flex-col rounded-xl bg-[var(--ink)] p-[22px]">
          {selected ? (
            <>
              <div className="mb-1 flex items-center justify-between">
                <span className="font-mono-ui text-[10px] tracking-[0.16em] text-[#8a8178]">ORGANIZAÇÃO</span>
                {selected.organization.id === activeOrganizationId ? <span className="rounded-[5px] bg-[rgba(224,122,78,0.18)] px-2 py-0.5 text-[10px] font-semibold tracking-[0.05em] text-[#E9A183]">ATIVA NA SESSÃO</span> : null}
              </div>
              <div className="mb-[18px] font-display text-[22px] font-bold tracking-[-0.02em] text-[var(--paper)]">{selected.organization.name}</div>
              <div className="mb-5 grid grid-cols-2 gap-x-4 gap-y-3.5">
                <div>
                  <p className="mb-[3px] font-mono-ui text-[10px] tracking-[0.08em] text-[#8a8178]">ID</p>
                  <p className="break-all font-mono-ui text-[12px] text-[#d4ccc2]">{selected.organization.id}</p>
                </div>
                <div>
                  <p className="mb-[3px] font-mono-ui text-[10px] tracking-[0.08em] text-[#8a8178]">SLUG</p>
                  <p className="font-mono-ui text-[12px] text-[#d4ccc2]">{selected.organization.slug ?? '—'}</p>
                </div>
                <div>
                  <p className="mb-[3px] font-mono-ui text-[10px] tracking-[0.08em] text-[#8a8178]">PAPEL</p>
                  <p className="text-[13px] text-[var(--paper)]">{selected.role.charAt(0).toUpperCase() + selected.role.slice(1)}</p>
                </div>
                <div>
                  <p className="mb-[3px] font-mono-ui text-[10px] tracking-[0.08em] text-[#8a8178]">STATUS</p>
                  <StatusBadge label={selected.active ? 'Ativa' : 'Inativa'} tone={selected.active ? 'good' : 'warning'} />
                </div>
              </div>
              <p className="mb-3 font-mono-ui text-[10px] tracking-[0.12em] text-[#8a8178]">PERMISSÕES · {selected.permissions.length}</p>
              <div className="flex flex-col gap-2">
                {selected.permissions.length === 0 ? (
                  <p className="text-[13px] text-[#8a8178]">Sem permissões explícitas neste vínculo.</p>
                ) : selected.permissions.map((permission) => (
                  <div key={permission} className="flex items-center gap-2.5">
                    <Icon name="check" size={13} className="flex-none text-[#7FCBAB]" />
                    <span className="font-mono-ui text-[12px] text-[#d4ccc2]">{permission}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-[13px] text-[#8a8178]">Selecione uma organização para ver papel e permissões.</p>
          )}
        </div>
      </div>

      {canReadPlatformOrganizations ? (
        <div className="mt-5 rounded-xl border border-[color:var(--border)] bg-[var(--card)] px-[22px] py-5">
          <div className="mb-3.5 flex items-start justify-between gap-4">
            <div>
              <h3 className="font-display text-[17px] font-bold text-[var(--ink)]">Organizações da plataforma</h3>
              <p className="mt-1 text-[13px] text-[var(--muted-2)]">Visualização somente leitura disponível para platform_admin.</p>
            </div>
            <span className="rounded-[5px] bg-[#F3E9D6] px-2 py-0.5 text-[10px] font-semibold tracking-[0.06em] text-[#946416]">READ ONLY</span>
          </div>
          {platformOrgsQuery.isLoading ? (
            <div className="rounded-[11px] border border-[color:var(--border)] bg-[var(--card)] px-4 py-6 text-sm text-[var(--muted)]">Carregando organizações da plataforma…</div>
          ) : platformOrgsQuery.isError ? (
            <div className="rounded-[11px] border border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.08)] px-4 py-6 text-sm leading-7 text-[#9e4120]">Não foi possível carregar as organizações da plataforma.</div>
          ) : (platformOrgsQuery.data?.items?.length ?? 0) === 0 ? (
            <div className="rounded-[11px] border border-dashed border-[color:var(--line)] bg-[var(--card)] px-4 py-6 text-sm leading-7 text-[var(--muted)]">Nenhuma organização da plataforma disponível.</div>
          ) : (
            <div className="overflow-hidden rounded-[11px] border border-[color:var(--border)]">
              <div className="grid grid-cols-[1.3fr_1fr_1fr_0.8fr] gap-3 border-b border-[color:var(--divider)] bg-[#F2EEE7] px-4 py-2.5 font-mono-ui text-[10px] tracking-[0.1em] text-[var(--nav-label)]">
                <span>NOME</span><span>LEGAL</span><span>SLUG / ID</span><span>STATUS</span>
              </div>
              {(platformOrgsQuery.data?.items ?? []).slice(0, 8).map((org) => (
                <div key={org.id} className="grid grid-cols-[1.3fr_1fr_1fr_0.8fr] gap-3 border-b border-[color:var(--row)] bg-[var(--card)] px-4 py-3 last:border-b-0">
                  <span className="truncate text-[13px] text-[var(--ink)]">{org.name}</span>
                  <span className="truncate text-[13px] text-[var(--muted)]">{org.legal_name}</span>
                  <span className="truncate font-mono-ui text-[11px] text-[var(--muted-2)]">{org.slug ?? '—'} · {org.id}</span>
                  <span className="flex items-center gap-2 truncate text-[13px] text-[var(--muted)]">
                    <span>{org.status}</span>
                    {canMutatePlatform ? (
                      <>
                        <Button type="button" size="sm" variant="secondary" onClick={() => { setConfirmAction({ kind: org.status === 'active' ? 'suspend' : 'reactivate', id: org.id, label: org.slug ?? org.name }); setConfirmText(''); setConfirmError(null); setConfirmFeedback(null) }}>
                          {org.status === 'active' ? 'Suspender' : 'Reativar'}
                        </Button>
                      </>
                    ) : null}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}

      {createOpen && canMutatePlatform ? (
        <div className="mt-5 rounded-xl border border-[color:var(--border)] bg-[var(--card)] px-[22px] py-5">
          <h3 className="font-display text-[17px] font-bold text-[var(--ink)]">Nova organização</h3>
          <p className="mt-1 text-[13px] text-[var(--muted-2)]">Criar organização já gera trilha auditável no backend.</p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <TextField label="Nome" value={createName} onChange={(e) => setCreateName(e.target.value)} />
            <TextField label="Razão social" value={createLegalName} onChange={(e) => setCreateLegalName(e.target.value)} />
            <TextField label="Tax ID" value={createTaxId} onChange={(e) => setCreateTaxId(e.target.value)} />
            <TextField label="Plano" value={createPlan} onChange={(e) => setCreatePlan(e.target.value)} />
            <TextField label="E-mail do líder" value={createLeaderEmail} onChange={(e) => setCreateLeaderEmail(e.target.value)} />
          </div>
          {createFeedback ? <div className="mt-4 rounded-[9px] border border-[#CFE6DA] bg-[#E7F1EB] px-3.5 py-3 text-[13px] leading-6 text-[#1F5540]">{createFeedback}</div> : null}
          {createError ? <div className="mt-4 rounded-[9px] border border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.08)] px-3.5 py-3 text-[13px] leading-6 text-[#9e4120]">{createError}</div> : null}
          <FormActions primaryLabel={adminMutations.createOrganization.isPending ? 'Criando…' : 'Criar organização'} secondaryLabel="Fechar" onPrimary={async () => {
            setCreateError(null); setCreateFeedback(null)
            try {
              await adminMutations.createOrganization.mutateAsync({ name: createName, legal_name: createLegalName, tax_id: createTaxId, plan: createPlan || null, leader_email: createLeaderEmail || null })
              setCreateFeedback('Organização criada e auditada.')
              setCreateOpen(false)
            } catch (error) { setCreateError(error instanceof Error ? error.message : 'Não foi possível criar a organização.') }
          }} onSecondary={() => setCreateOpen(false)} primaryDisabled={!createName.trim() || !createLegalName.trim() || !createTaxId.trim() || adminMutations.createOrganization.isPending} primaryHint="A API grava a ação em audit logs." />
        </div>
      ) : null}

      {confirmAction && canMutatePlatform ? (
        <div className="mt-5 rounded-xl border border-[color:var(--border)] bg-[var(--card)] px-[22px] py-5">
          <h3 className="font-display text-[17px] font-bold text-[var(--ink)]">Confirmação de {confirmAction.kind === 'suspend' ? 'suspensão' : 'reativação'}</h3>
          <p className="mt-1 text-[13px] text-[var(--muted-2)]">Digite <span className="font-semibold">{confirmAction.label}</span> para continuar.</p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <TextField label="Confirmação" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} placeholder={confirmAction.label} />
          </div>
          {confirmFeedback ? <div className="mt-4 rounded-[9px] border border-[#CFE6DA] bg-[#E7F1EB] px-3.5 py-3 text-[13px] leading-6 text-[#1F5540]">{confirmFeedback}</div> : null}
          {confirmError ? <div className="mt-4 rounded-[9px] border border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.08)] px-3.5 py-3 text-[13px] leading-6 text-[#9e4120]">{confirmError}</div> : null}
          <FormActions primaryLabel={confirmAction.kind === 'suspend' ? 'Suspender' : 'Reativar'} secondaryLabel="Cancelar" onPrimary={async () => {
            if (confirmText.trim() !== confirmAction.label) return
            try {
              if (confirmAction.kind === 'suspend') await adminMutations.suspendOrganization.mutateAsync(confirmAction.id)
              else await adminMutations.reactivateOrganization.mutateAsync(confirmAction.id)
              setConfirmFeedback('Ação auditável concluída.')
              setConfirmAction(null)
              setConfirmText('')
            } catch (error) { setConfirmError(error instanceof Error ? error.message : 'Não foi possível concluir a ação.') }
          }} onSecondary={() => setConfirmAction(null)} primaryDisabled={confirmText.trim() !== confirmAction.label || adminMutations.suspendOrganization.isPending || adminMutations.reactivateOrganization.isPending} primaryHint="A ação exige confirmação forte e gera auditoria." />
        </div>
      ) : null}
    </div>
  )
}
