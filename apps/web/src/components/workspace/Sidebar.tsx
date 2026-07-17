import { Icon } from '../ui/icons'
import { MonogramMark } from '../ui/brand'
import type { AppSection } from '../../navigation/routes'
import { initialsFrom } from '../../utils/formatters'

export type WorkspaceNavItem = { id: AppSection; label: string; hint: string; path: string; icon: import('../ui/icons').IconName; group: string }

export const workspaceNavItems: WorkspaceNavItem[] = [
  { id: 'dashboard', label: 'Dashboard', hint: 'Visão geral', path: '/dashboard', icon: 'grid', group: 'Visão geral' },
  { id: 'incidents', label: 'Incidentes', hint: 'Triagem e ação', path: '/dashboard/incidents', icon: 'alert-triangle', group: 'Operação' },
  { id: 'evidence', label: 'Evidências', hint: 'Snapshot e clipes', path: '/dashboard/evidence', icon: 'video', group: 'Operação' },
  { id: 'operations', label: 'Operações/Câmeras', hint: 'Unidades, zonas e EPI', path: '/dashboard/operations', icon: 'activity', group: 'Operação' },
  { id: 'organizations', label: 'Organizações', hint: 'Tenants e unidades', path: '/dashboard/organizations', icon: 'building', group: 'Administração' },
  { id: 'users', label: 'Usuários', hint: 'Acesso e papéis', path: '/dashboard/users', icon: 'users', group: 'Administração' },
  { id: 'audit', label: 'Auditoria', hint: 'Trilha de eventos', path: '/dashboard/audit', icon: 'file-text', group: 'Administração' },
  { id: 'settings', label: 'Configurações', hint: 'Preferências do sistema', path: '/dashboard/settings', icon: 'settings', group: 'Sistema' },
]

const navGroupOrder = ['Visão geral', 'Operação', 'Administração'] as const

function WorkspaceNav({ activeSection, onSelect, openBadge }: { activeSection: AppSection; onSelect: (section: AppSection) => void; openBadge: number }) {
  return (
    <nav className="flex-1 overflow-auto px-3.5 py-2.5">
      {navGroupOrder.map((group) => (
        <div key={group}>
          <div className="px-2.5 pb-2 pt-2.5 font-mono-ui text-[10px] uppercase tracking-[0.16em] text-[var(--nav-label)]">{group}</div>
          {workspaceNavItems.filter((item) => item.group === group).map((item) => {
            const active = item.id === activeSection
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelect(item.id)}
                aria-current={active ? 'page' : undefined}
                className={`relative flex w-full items-center gap-[11px] rounded-lg px-2.5 py-[9px] text-sm transition ${active ? 'bg-[var(--nav-active-bg)] font-semibold text-[var(--nav-active-text)]' : 'text-[var(--nav-text)] hover:bg-[rgba(32,27,24,0.04)]'}`}
              >
                {active ? <span className="absolute left-0 top-[7px] bottom-[7px] w-[3px] rounded-full bg-[var(--accent)]" /> : null}
                <Icon name={item.icon} size={18} className={active ? 'text-[var(--accent)]' : 'text-[var(--muted-2)]'} />
                <span className="flex-1 text-left">{item.label}</span>
                {item.id === 'incidents' && openBadge > 0 ? (
                  <span className="rounded-full bg-[var(--accent)] px-[7px] py-px font-mono-ui text-[11px] font-semibold text-white">{openBadge}</span>
                ) : null}
              </button>
            )
          })}
        </div>
      ))}
    </nav>
  )
}

export function Sidebar({
  orgName,
  sitesCount,
  activeCamerasCount,
  userName,
  userRole,
  activeSection,
  openBadge,
  connection,
  onSelect,
  onHome,
  onSettings,
  onLogout,
  onClose,
}: {
  orgName: string
  sitesCount: number
  activeCamerasCount: number
  userName: string
  userRole: string
  activeSection: AppSection
  openBadge: number
  connection: { label: string; dot: string }
  onSelect: (section: AppSection) => void
  onHome: () => void
  onSettings: () => void
  onLogout: () => void
  onClose?: () => void
}) {
  return (
    <div className="flex h-full flex-col bg-[var(--card)]">
      <div className="flex h-[61px] flex-none items-center gap-[11px] border-b border-[color:var(--divider)] px-5">
        <button type="button" onClick={onHome} className="flex items-center gap-[11px] text-left">
          <MonogramMark className="h-[30px] w-[30px]" />
          <span className="flex flex-col leading-none">
            <span className="text-[15px] font-semibold tracking-[0.02em] text-[var(--ink)]">VIGIA</span>
            <span className="mt-[3px] font-mono-ui text-[7px] uppercase tracking-[0.34em] text-[var(--label)]">SAFETY</span>
          </span>
        </button>
        {onClose ? (
          <button type="button" onClick={onClose} aria-label="Fechar navegação" className="ml-auto grid h-8 w-8 place-items-center rounded-lg text-[var(--muted-2)] transition hover:bg-[rgba(32,27,24,0.05)]">
            <Icon name="x" size={18} />
          </button>
        ) : null}
      </div>

      <div className="px-3.5 pb-1.5 pt-3.5">
        <div className="flex items-center gap-2.5 rounded-[9px] border border-[color:var(--border)] bg-[var(--paper)] px-[11px] py-[9px]">
          <span className="grid h-[26px] w-[26px] flex-none place-items-center rounded-[7px] bg-[var(--ink)] font-display text-[13px] font-bold text-[var(--paper)]">{orgName.trim().charAt(0).toUpperCase() || 'V'}</span>
          <span className="min-w-0 flex-1 leading-tight">
            <span className="block truncate text-[13px] font-semibold text-[var(--ink)]">{orgName}</span>
            <span className="font-mono-ui text-[10px] text-[var(--label)]">{sitesCount} unidade{sitesCount === 1 ? '' : 's'}</span>
          </span>
          <Icon name="chevron-down" size={14} className="flex-none text-[var(--label)]" />
        </div>
      </div>

      <WorkspaceNav activeSection={activeSection} onSelect={onSelect} openBadge={openBadge} />

      <div className="flex-none border-t border-[color:var(--divider)] px-3.5 py-3">
        <div className="mb-1.5 flex items-center justify-between px-2.5 py-1.5">
          <span className="flex items-center gap-2 text-xs text-[var(--muted)]">
            <span className="pulse-dot h-[7px] w-[7px] rounded-full" style={{ background: connection.dot }} />
            {connection.label}
          </span>
          <span className="font-mono-ui text-[10px] text-[var(--nav-label)]">{activeCamerasCount} câm</span>
        </div>
        <button type="button" onClick={onSettings} className={`mb-1.5 flex w-full items-center gap-[11px] rounded-lg px-2.5 py-[9px] text-sm transition ${activeSection === 'settings' ? 'bg-[var(--nav-active-bg)] font-semibold text-[var(--nav-active-text)]' : 'text-[var(--nav-text)] hover:bg-[rgba(32,27,24,0.04)]'}`}>
          <Icon name="settings" size={18} className={activeSection === 'settings' ? 'text-[var(--accent)]' : 'text-[var(--muted-2)]'} />
          Configurações
        </button>
        <div className="flex items-center gap-2.5 rounded-[9px] bg-[var(--paper)] px-2.5 py-2">
          <span className="grid h-[30px] w-[30px] flex-none place-items-center rounded-lg bg-[var(--accent)] text-[13px] font-semibold text-white">{initialsFrom(userName)}</span>
          <span className="min-w-0 flex-1 leading-[1.25]">
            <span className="block truncate text-[13px] font-semibold text-[var(--ink)]">{userName}</span>
            <span className="block truncate text-[11px] text-[var(--label)]">{userRole || 'Membro'}</span>
          </span>
          <button type="button" onClick={onLogout} aria-label="Sair" title="Sair" className="flex-none rounded-md p-1 text-[var(--label)] transition hover:text-[var(--accent)]">
            <Icon name="log-out" size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
