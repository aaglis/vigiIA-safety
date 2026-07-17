import { useEffect, useMemo, useState } from 'react'
import type { Membership } from '../../api/auth'
import type { MemberRecord } from '../../api/members'
import type { OrganizationInvite } from '../../api/invites'
import { Button, DataCard, FormActions, Modal, SelectField, StatusBadge, TextField } from '../../components/ui/brand'
import { Icon } from '../../components/ui/icons'
import { useInviteActions, useInvites, useMemberActions, useMembers } from '../../queries/hooks'

type UserRow = {
  id: string
  name: string
  email: string
  role: string
  organizationName: string
  organizationId: string
  status: 'active' | 'inactive' | 'pending'
  lastActivity: string
  permissions: string[]
  isCurrentUser: boolean
  source: 'membership' | 'invite'
  inviteId?: string
}

const STATUS_BADGE: Record<UserRow['status'], { label: string; bg: string; color: string }> = {
  active: { label: 'ATIVO', bg: '#E4EFE9', color: '#1F6B4A' },
  pending: { label: 'PENDENTE', bg: '#F3E9D6', color: '#946416' },
  inactive: { label: 'INATIVO', bg: '#EEEAE3', color: '#7C756C' },
}

const INVITE_ROLES = ['manager', 'auditor_viewer', 'org_admin']

function initials(value: string) {
  const parts = value.trim().split(/[\s@._-]+/).filter(Boolean)
  if (parts.length === 0) return '—'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

function formatInviteExpiration(invite: OrganizationInvite) {
  if (invite.status === 'accepted') return 'Aceito'
  if (invite.status === 'revoked') return 'Revogado'
  if (invite.status === 'expired') return 'Expirado'
  const date = new Date(invite.expires_at)
  return Number.isNaN(date.getTime()) ? 'Pendente' : `Expira em ${new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' }).format(date)}`
}

export function UsersPage({
  memberships,
  userName,
  userEmail,
  activeOrganizationId,
  activePermissions,
  liveLabel,
  isLoading,
}: {
  memberships: Membership[]
  userName: string
  userEmail: string
  activeOrganizationName: string
  activeOrganizationId: string | null
  activePermissions: string[]
  liveLabel: string
  isLoading: boolean
}) {
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | UserRow['status']>('all')
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null)
  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('manager')
  const [touched, setTouched] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [memberModalOpen, setMemberModalOpen] = useState(false)
  const [memberRole, setMemberRole] = useState('')
  const [memberActive, setMemberActive] = useState(true)

  const canListInvites = liveLabel === 'Conectado à API' && activePermissions.includes('org.members.manage')
  const canCreateInvites = liveLabel === 'Conectado à API' && activePermissions.includes('org.members.invite')
  const canEditMembers = liveLabel === 'Conectado à API' && (activePermissions.includes('org.members.manage') || activePermissions.includes('org.roles.manage'))
  const invitesQuery = useInvites(activeOrganizationId, canListInvites)
  const membersQuery = useMembers(activeOrganizationId, liveLabel === 'Conectado à API' && !!activeOrganizationId)
  const inviteActions = useInviteActions(activeOrganizationId)
  const memberActions = useMemberActions(activeOrganizationId)
  const inviteBusy = inviteActions.create.isPending || inviteActions.resend.isPending || inviteActions.revoke.isPending
  const memberBusy = memberActions.update.isPending || memberActions.deactivate.isPending
  const invites = invitesQuery.data?.items ?? []
  const liveMembers = membersQuery.data?.items ?? []

  const rows = useMemo<UserRow[]>(() => {
    if (liveLabel === 'Conectado à API' && activeOrganizationId && liveMembers.length > 0) {
      return liveMembers.map((member) => ({
        id: member.user.id,
        name: member.user.full_name || member.user.email,
        email: member.user.email,
        role: member.role,
        organizationName: member.organization.name,
        organizationId: member.organization.id,
        status: member.active ? 'active' : 'inactive',
        lastActivity: member.active ? 'Agora' : 'Inativo',
        permissions: member.permissions,
        isCurrentUser: member.user.email === userEmail,
        source: 'membership',
      }))
    }
    return memberships.map((membership, index) => ({
      id: `${membership.organization.id}:${membership.role}:${index}`,
      name: userName || userEmail,
      email: userEmail,
      role: membership.role,
      organizationName: membership.organization.name,
      organizationId: membership.organization.id,
      status: membership.active ? 'active' : 'inactive',
      lastActivity: membership.active && membership.organization.id === activeOrganizationId ? 'Agora' : 'Sem telemetria',
      permissions: membership.permissions,
      isCurrentUser: true,
      source: 'membership',
    }))
  }, [activeOrganizationId, liveLabel, liveMembers, memberships, userEmail, userName])

  const inviteRows = useMemo<UserRow[]>(() => invites.map((invite) => ({
    id: `invite:${invite.id}`,
    name: invite.email,
    email: invite.email,
    role: invite.role,
    organizationName: memberships.find((membership) => membership.organization.id === invite.organization_id)?.organization.name ?? 'Organização ativa',
    organizationId: invite.organization_id,
    status: invite.status === 'pending' ? 'pending' : 'inactive',
    lastActivity: formatInviteExpiration(invite),
    permissions: [],
    isCurrentUser: false,
    source: 'invite',
    inviteId: invite.id,
  })), [invites, memberships])

  const allRows = useMemo(() => rows.concat(inviteRows), [inviteRows, rows])

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return allRows.filter((row) => {
      const matchesQuery = !q || row.name.toLowerCase().includes(q) || row.email.toLowerCase().includes(q) || row.role.toLowerCase().includes(q) || row.organizationName.toLowerCase().includes(q)
      const matchesStatus = statusFilter === 'all' || row.status === statusFilter
      const matchesRole = roleFilter === 'all' || row.role.toLowerCase() === roleFilter
      return matchesQuery && matchesStatus && matchesRole
    })
  }, [allRows, query, roleFilter, statusFilter])

  useEffect(() => {
    if (selectedUserId && filtered.some((row) => row.id === selectedUserId)) return
    setSelectedUserId(filtered[0]?.id ?? allRows[0]?.id ?? null)
  }, [allRows, filtered, selectedUserId])

  useEffect(() => {
    if (!inviteOpen) return
    setInviteEmail('')
    setInviteRole('manager')
    setTouched(false)
    setFeedback(null)
    setError(null)
  }, [inviteOpen])

  const selected = filtered.find((row) => row.id === selectedUserId) ?? filtered[0] ?? allRows[0] ?? null
  const selectedMember = selected && selected.source === 'membership' && liveMembers.find((member) => member.user.id === selected.id)
  const editableMember = selectedMember ?? (selected?.source === 'membership' && !selected.id.includes(':') ? selected : null)
  const roleOptions = Array.from(new Set(allRows.map((row: UserRow) => row.role.toLowerCase()).concat(INVITE_ROLES))).sort()
  const activeCount = rows.filter((row: UserRow) => row.status === 'active').length
  const pendingCount = inviteRows.filter((row: UserRow) => row.status === 'pending').length
  const emailError = touched && !inviteEmail.trim()
    ? 'Informe um e-mail para o convite.'
    : touched && !/^\S+@\S+\.\S+$/.test(inviteEmail.trim())
      ? 'Digite um e-mail válido.'
      : ''

  const submitInvite = async () => {
    setTouched(true)
    setFeedback(null)
    setError(null)
    if (!inviteEmail.trim() || emailError) return
    try {
      await inviteActions.create.mutateAsync({ email: inviteEmail.trim(), role: inviteRole })
      setFeedback('Convite criado no backend. O token não é exibido na interface por segurança.')
      setInviteEmail('')
      setTouched(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível enviar o convite.')
    }
  }

  const openEditAccess = () => {
    if (!editableMember) return
    setMemberRole(editableMember.role)
    setMemberActive('active' in editableMember ? editableMember.active : editableMember.status === 'active')
    setMemberModalOpen(true)
  }

  const submitMemberEdit = async () => {
    if (!editableMember || !activeOrganizationId) return
    const userId = 'user' in editableMember ? editableMember.user.id : editableMember.id
    const currentRole = editableMember.role
    const currentActive = 'active' in editableMember ? editableMember.active : editableMember.status === 'active'
    setFeedback(null)
    setError(null)
    try {
      if (!memberActive) {
        await memberActions.deactivate.mutateAsync(userId)
      }
      if (memberRole && memberRole !== currentRole) {
        await memberActions.update.mutateAsync({ userId, role: memberRole, active: memberActive })
      } else if (memberActive !== currentActive) {
        await memberActions.update.mutateAsync({ userId, active: memberActive })
      }
      setFeedback('Acesso atualizado no backend.')
      setMemberModalOpen(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível atualizar o acesso.')
    }
  }

  const resendInvite = async (inviteId: string) => {
    setFeedback(null)
    setError(null)
    try {
      await inviteActions.resend.mutateAsync(inviteId)
      setFeedback('Convite reenviado. O token não é exibido na interface por segurança.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível reenviar o convite.')
    }
  }

  const revokeInvite = async (inviteId: string) => {
    setFeedback(null)
    setError(null)
    try {
      await inviteActions.revoke.mutateAsync(inviteId)
      setFeedback('Convite revogado no backend.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível revogar o convite.')
    }
  }

  return (
    <div className="mx-auto max-w-[1200px]">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-[26px] font-bold leading-none tracking-[-0.025em] text-[var(--ink)]">Convites, vínculos e acesso</h2>
          <p className="mt-1.5 text-sm text-[var(--muted)]">Membros da organização ativa e seus papéis. Workers monitorados não aparecem aqui.</p>
        </div>
        <Button type="button" onClick={() => setInviteOpen(true)} className="px-4"><Icon name="plus" size={15} /> Convidar usuário</Button>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <DataCard label="Usuários vinculados" value={rows.length} />
        <DataCard label="Ativos" value={activeCount} tone="good" />
        <DataCard label="Convites pendentes" value={pendingCount} detail={pendingCount > 0 ? 'aguardando' : 'sem fila'} tone={pendingCount > 0 ? 'warning' : 'neutral'} />
      </div>

      {!canListInvites ? (
        <div className="mb-4 rounded-[10px] border border-[#E3D8C8] bg-[#F7F0E2] px-4 py-3 text-[13px] leading-6 text-[#5a4a2a]">
          Convites reais já existem no backend. Esta sessão ainda não expõe `org.members.manage`, então a tela mostra os vínculos de `/auth/me` e mantém envio protegido por permissão.
        </div>
      ) : invitesQuery.isError ? (
        <div className="mb-4 rounded-[10px] border border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.08)] px-4 py-3 text-[13px] leading-6 text-[#9e4120]">Não foi possível carregar convites reais agora.</div>
      ) : null}
      {feedback ? <div className="mb-4 rounded-[10px] border border-[#CFE0D6] bg-[#EAF3EE] px-4 py-3 text-[13px] leading-6 text-[#1F6B4A]">{feedback}</div> : null}
      {error ? <div className="mb-4 rounded-[10px] border border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.08)] px-4 py-3 text-[13px] leading-6 text-[#9e4120]">{error}</div> : null}

      <div className="mb-3.5 flex flex-wrap items-center gap-2">
        <div className="flex h-9 max-w-[320px] flex-1 items-center gap-2.5 rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-3">
          <Icon name="search" size={15} className="flex-none text-[var(--nav-label)]" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Nome ou e-mail…" className="w-full bg-transparent text-[13px] text-[var(--ink)] outline-none placeholder:text-[var(--nav-label)]" />
        </div>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as 'all' | UserRow['status'])} className="h-9 rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-2.5 text-[13px] text-[var(--muted)] outline-none focus:border-[rgba(193,85,43,0.5)]">
          <option value="all">Status: Todos</option>
          <option value="active">Ativo</option>
          <option value="pending">Pendente</option>
          <option value="inactive">Inativo</option>
        </select>
        <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="h-9 rounded-lg border border-[color:var(--line)] bg-[var(--card)] px-2.5 text-[13px] text-[var(--muted)] outline-none focus:border-[rgba(193,85,43,0.5)]">
          <option value="all">Papel: Todos</option>
          {roleOptions.map((role) => <option key={role} value={role}>{role}</option>)}
        </select>
      </div>

      <div className="grid gap-3.5 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="overflow-hidden rounded-xl border border-[color:var(--border)] bg-[var(--card)]">
          <div className="grid grid-cols-[2fr_1.2fr_1fr_1fr] gap-3 border-b border-[color:var(--divider)] px-[18px] py-2.5 font-mono-ui text-[10px] tracking-[0.1em] text-[var(--nav-label)]">
            <span>NOME / E-MAIL</span><span>PAPEL</span><span>STATUS</span><span className="text-right">ATIVIDADE</span>
          </div>
          {isLoading || invitesQuery.isLoading ? (
            <p className="px-[18px] py-6 text-sm text-[var(--muted)]">Carregando usuários…</p>
          ) : filtered.length === 0 ? (
            <p className="px-[18px] py-6 text-sm leading-7 text-[var(--muted)]">Nenhum usuário corresponde aos filtros.</p>
          ) : filtered.map((row) => {
            const badge = STATUS_BADGE[row.status]
            const isSelected = selected?.id === row.id
            return (
              <button key={row.id} type="button" onClick={() => setSelectedUserId(row.id)} className={`relative grid w-full grid-cols-[2fr_1.2fr_1fr_1fr] items-center gap-3 border-b border-[color:var(--row)] px-[18px] py-3 text-left transition last:border-b-0 hover:bg-[rgba(193,85,43,0.03)] ${isSelected ? 'bg-[#F9EEE7]' : ''} ${row.status === 'inactive' ? 'opacity-70' : ''}`}>
                {isSelected ? <span className="absolute inset-y-0 left-0 w-[3px] bg-[var(--accent)]" /> : null}
                <span className="flex items-center gap-2.5">
                  <span className="grid h-8 w-8 flex-none place-items-center rounded-lg text-xs font-semibold" style={isSelected ? { background: '#C1552B', color: '#fff' } : { background: '#EDE9E1', color: '#7C756C' }}>{initials(row.name)}</span>
                  <span className="min-w-0">
                    <span className="block truncate text-[13px] font-semibold text-[var(--ink)]">{row.name}{row.isCurrentUser ? <span className="font-normal text-[var(--nav-label)]"> (você)</span> : null}</span>
                    <span className="block truncate font-mono-ui text-[11px] text-[var(--muted-2)]">{row.email}</span>
                  </span>
                </span>
                <span className="min-w-0">
                  <span className="block text-[13px] capitalize text-[var(--ink)]">{row.role}</span>
                  <span className="block font-mono-ui text-[10px] text-[var(--nav-label)]">{row.source === 'invite' ? 'convite real' : `${row.permissions.length} ${row.permissions.length === 1 ? 'permissão' : 'permissões'}`}</span>
                </span>
                <StatusBadge label={badge.label} tone={row.status === 'active' ? 'good' : row.status === 'pending' ? 'warning' : 'dark'} className="justify-self-start rounded-[5px] px-2 py-0.5 text-[10px] font-semibold" />
                <span className="text-right font-mono-ui text-[11px] text-[var(--muted-2)]">{row.lastActivity}</span>
              </button>
            )
          })}
        </div>

        <div className="flex flex-col rounded-xl bg-[var(--ink)] p-[22px]">
          {selected ? (
            <>
              <div className="mb-[18px] flex items-center gap-3">
                <span className="grid h-11 w-11 flex-none place-items-center rounded-[11px] bg-[var(--accent)] text-base font-semibold text-white">{initials(selected.name)}</span>
                <div className="min-w-0"><p className="truncate font-display text-[18px] font-bold leading-[1.1] text-[var(--paper)]">{selected.name}</p><p className="mt-0.5 truncate font-mono-ui text-[11px] text-[#8a8178]">{selected.email}</p></div>
              </div>
              <div className="mb-5 grid grid-cols-2 gap-x-4 gap-y-3.5">
                <div><p className="mb-[3px] font-mono-ui text-[10px] tracking-[0.08em] text-[#8a8178]">PAPEL</p><p className="text-[13px] capitalize text-[var(--paper)]">{selected.role}</p></div>
                <div><p className="mb-[3px] font-mono-ui text-[10px] tracking-[0.08em] text-[#8a8178]">ORGANIZAÇÃO</p><p className="truncate text-[13px] text-[var(--paper)]">{selected.organizationName}</p></div>
                <div><p className="mb-[3px] font-mono-ui text-[10px] tracking-[0.08em] text-[#8a8178]">STATUS</p><StatusBadge label={STATUS_BADGE[selected.status].label.charAt(0) + STATUS_BADGE[selected.status].label.slice(1).toLowerCase()} tone={selected.status === 'active' ? 'good' : selected.status === 'pending' ? 'warning' : 'dark'} /></div>
                <div><p className="mb-[3px] font-mono-ui text-[10px] tracking-[0.08em] text-[#8a8178]">ATIVIDADE</p><p className="text-[13px] text-[var(--paper)]">{selected.lastActivity}</p></div>
              </div>
              <p className="mb-3 font-mono-ui text-[10px] tracking-[0.12em] text-[#8a8178]">{selected.source === 'invite' ? 'CONVITE' : `PERMISSÕES · ${selected.permissions.length}`}</p>
              {selected.source === 'invite' ? <p className="text-[13px] leading-6 text-[#d4ccc2]">Convite pendente carregado de `/organizations/:id/invites`. Reenvio e revogação usam o backend, sem expor token no frontend.</p> : <div className="flex flex-wrap gap-1.5">{selected.permissions.length === 0 ? <p className="text-[13px] text-[#8a8178]">Sem permissões registradas.</p> : selected.permissions.map((permission) => <span key={permission} className="rounded-md bg-[#2A241F] px-2.5 py-[3px] font-mono-ui text-[11px] text-[#d4ccc2]">{permission}</span>)}</div>}
              <div className="flex-1" />
              {selected.source === 'invite' && selected.inviteId ? (
                <div className="mt-5 grid gap-2">
                  <Button type="button" disabled={inviteBusy || !canCreateInvites} variant="secondary" className="w-full" onClick={() => void resendInvite(selected.inviteId!)}>Reenviar convite</Button>
                  <Button type="button" disabled={inviteBusy || !canListInvites} variant="danger" className="w-full" onClick={() => void revokeInvite(selected.inviteId!)}>Revogar convite</Button>
                </div>
              ) : <Button type="button" disabled={!canEditMembers || !editableMember || memberBusy} title={!canEditMembers ? 'Sem permissão' : ''} variant="secondary" className="mt-5 w-full" onClick={openEditAccess}>Editar acesso</Button>}
            </>
          ) : <p className="text-[13px] text-[#8a8178]">Selecione um usuário para ver acesso e permissões.</p>}
        </div>
      </div>

      <Modal open={inviteOpen} onClose={() => setInviteOpen(false)} title="Convidar usuário" description={canCreateInvites ? 'Cria um convite real no backend da organização ativa.' : 'Backend de convites disponível, mas esta sessão não tem permissão org.members.invite.'}>
        <div className="space-y-5">
          <TextField label="E-mail" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} onBlur={() => setTouched(true)} placeholder="nome@empresa.com" helperText="O convite é criado no backend; tokens não são exibidos na interface." errorText={emailError} />
          <SelectField label="Papel" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)} helperText="Papéis aceitos hoje pelo serviço de convites.">{INVITE_ROLES.map((role) => <option key={role} value={role}>{role}</option>)}</SelectField>
          <div className="rounded-[10px] border border-[rgba(201,138,43,0.22)] bg-[rgba(201,138,43,0.1)] p-4 text-sm leading-7 text-[#7a5314]">Prévia: {inviteEmail.trim() || '—'} · {inviteRole} · organização ativa</div>
          <FormActions primaryLabel={inviteBusy ? 'Enviando…' : 'Enviar convite'} secondaryLabel="Cancelar" onSecondary={() => setInviteOpen(false)} onPrimary={() => void submitInvite()} primaryDisabled={!canCreateInvites || inviteBusy} primaryHint={canCreateInvites ? 'Usa POST /organizations/{id}/invites.' : 'Permissão org.members.invite ausente nesta sessão.'} />
        </div>
      </Modal>

      <Modal open={memberModalOpen} onClose={() => setMemberModalOpen(false)} title="Editar acesso" description="Atualiza papel e estado de acesso no backend.">
        <div className="space-y-5">
          <SelectField label="Papel" value={memberRole} onChange={(e) => setMemberRole(e.target.value)} helperText="Use PATCH para alteração de papel e status.">
            {roleOptions.map((role) => <option key={role} value={role}>{role}</option>)}
          </SelectField>
          <SelectField label="Status" value={memberActive ? 'active' : 'inactive'} onChange={(e) => setMemberActive(e.target.value === 'active')} helperText="Desativação usa DELETE no backend quando aplicável.">
            <option value="active">Ativo</option>
            <option value="inactive">Inativo</option>
          </SelectField>
          <div className="rounded-[10px] border border-[rgba(201,138,43,0.22)] bg-[rgba(201,138,43,0.1)] p-4 text-sm leading-7 text-[#7a5314]">{selected?.name} · {selected?.role} · {memberActive ? 'ativo' : 'inativo'}</div>
          <FormActions primaryLabel={memberBusy ? 'Salvando…' : 'Salvar mudanças'} secondaryLabel="Cancelar" onSecondary={() => setMemberModalOpen(false)} onPrimary={() => void submitMemberEdit()} primaryDisabled={!canEditMembers || memberBusy} primaryHint="Falhas de permissão, CSRF ou owner final aparecem como erro do backend." />
        </div>
      </Modal>
    </div>
  )
}
