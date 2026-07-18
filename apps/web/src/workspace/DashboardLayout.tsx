import type { ReactNode } from 'react'
import { Icon } from '../components/ui/icons'
import { Sidebar } from '../components/workspace/Sidebar'
import type { AppSection } from '../navigation/routes'

type ConnectionTone = { label: string; bg: string; border: string; color: string; dot: string }

type DashboardLayoutProps = {
  children: ReactNode
  banner: string | null
  dashboardError: string | null
  operationsError: string | null
  onRetryOperations: () => void
  activeOrganizationName: string
  sitesCount: number
  activeCamerasCount: number
  userName: string
  userRole: string
  activeSection: AppSection
  openBadge: number
  connection: { label: string; dot: string }
  connectionTone: ConnectionTone
  onSelect: (section: AppSection) => void
  onHome: () => void
  onSettings: () => void
  onLogout: () => void
  mobileNavOpen: boolean
  onOpenMobileNav: () => void
  onCloseMobileNav: () => void
  activeWorkspaceLabel: string
  initials: string
  showDashboardError: boolean
}

export function DashboardLayout({
  children,
  banner,
  dashboardError,
  operationsError,
  onRetryOperations,
  activeOrganizationName,
  sitesCount,
  activeCamerasCount,
  userName,
  userRole,
  activeSection,
  openBadge,
  connection,
  connectionTone,
  onSelect,
  onHome,
  onSettings,
  onLogout,
  mobileNavOpen,
  onOpenMobileNav,
  onCloseMobileNav,
  activeWorkspaceLabel,
  initials,
  showDashboardError,
}: DashboardLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-[var(--paper)] text-[var(--ink)]">
      <aside className="hidden w-[250px] flex-none border-r border-[color:var(--border)] lg:block">
        <Sidebar
          orgName={activeOrganizationName}
          sitesCount={sitesCount}
          activeCamerasCount={activeCamerasCount}
          userName={userName}
          userRole={userRole}
          activeSection={activeSection}
          openBadge={openBadge}
          connection={connection}
          onSelect={onSelect}
          onHome={onHome}
          onSettings={onSettings}
          onLogout={onLogout}
        />
      </aside>

      {mobileNavOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button type="button" aria-label="Fechar navegação" onClick={onCloseMobileNav} className="absolute inset-0 bg-[rgba(32,27,24,0.38)]" />
          <div className="absolute left-0 top-0 h-full w-[min(84vw,280px)] border-r border-[color:var(--border)] shadow-[0_24px_80px_rgba(32,27,24,0.2)]">
            <Sidebar
              orgName={activeOrganizationName}
              sitesCount={sitesCount}
              activeCamerasCount={activeCamerasCount}
              userName={userName}
              userRole={userRole}
              activeSection={activeSection}
              openBadge={openBadge}
              connection={connection}
              onSelect={onSelect}
              onHome={onHome}
              onSettings={onSettings}
              onLogout={onLogout}
              onClose={onCloseMobileNav}
            />
          </div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[61px] flex-none items-center justify-between gap-4 border-b border-[color:var(--border)] bg-[var(--card)] px-5 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button type="button" onClick={onOpenMobileNav} aria-label="Abrir navegação" className="grid h-9 w-9 flex-none place-items-center rounded-lg border border-[color:var(--line)] bg-[var(--paper)] text-[var(--muted)] lg:hidden">
              <Icon name="menu" size={18} />
            </button>
            <div className="min-w-0">
              <p className="truncate font-mono-ui text-[11px] tracking-[0.06em] text-[var(--nav-label)]">Início / {activeWorkspaceLabel}</p>
              <p className="truncate font-display text-[19px] font-bold leading-none tracking-[-0.02em] text-[var(--ink)]">{activeWorkspaceLabel}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 sm:gap-3.5">
            <div className="hidden h-[38px] w-[230px] items-center gap-2.5 rounded-[9px] border border-[color:var(--line)] bg-[var(--paper)] px-3 xl:flex">
              <Icon name="search" size={16} className="flex-none text-[var(--nav-label)]" />
              <span className="flex-1 truncate text-[13px] text-[var(--nav-label)]">Buscar incidente, câmera…</span>
              <span className="flex-none rounded-[5px] border border-[color:var(--line)] px-[5px] py-px font-mono-ui text-[11px] text-[#bbb4a8]">⌘K</span>
            </div>
            <span className="hidden items-center gap-2 rounded-full border px-2.5 py-[5px] text-xs font-medium sm:inline-flex" style={{ background: connectionTone.bg, borderColor: connectionTone.border, color: connectionTone.color }}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: connectionTone.dot }} />
              {connectionTone.label}
            </span>
            <span className="hidden h-6 w-px bg-[var(--border)] sm:block" />
            <button type="button" className="relative grid h-[38px] w-[38px] place-items-center rounded-[9px] border border-[color:var(--line)] bg-[var(--paper)] text-[var(--muted)] transition hover:text-[var(--ink)]">
              <Icon name="bell" size={18} />
              {openBadge > 0 ? <span className="absolute right-2 top-[7px] h-[7px] w-[7px] rounded-full border-[1.5px] border-[var(--card)] bg-[var(--accent)]" /> : null}
            </button>
            <span className="grid h-[38px] w-[38px] place-items-center rounded-[9px] bg-[var(--accent)] text-[13px] font-semibold text-white">{initials}</span>
          </div>
        </header>

        <main className="flex-1 overflow-auto px-5 py-6 sm:px-8 sm:py-7 lg:px-10">
          {banner ? <div className="mx-auto mb-4 max-w-[1120px] rounded-[10px] border border-[rgba(47,125,87,0.24)] bg-[rgba(47,125,87,0.08)] px-4 py-3 text-sm text-[#236444]">{banner}</div> : null}
          {showDashboardError && dashboardError ? <div className="mx-auto mb-4 max-w-[1120px] rounded-[10px] border border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.07)] px-4 py-3 text-sm text-[#9e4120]">{dashboardError}</div> : null}
          {operationsError ? <div className="mx-auto mb-4 max-w-[1120px] rounded-[10px] border border-[rgba(193,85,43,0.22)] bg-[rgba(193,85,43,0.07)] px-4 py-3 text-sm text-[#9e4120]"><div className="flex flex-wrap items-center justify-between gap-3"><p>{operationsError}</p><button type="button" onClick={onRetryOperations} className="font-medium text-[var(--ink)] underline decoration-[rgba(32,27,24,0.3)] underline-offset-4 transition hover:opacity-80">Tentar atualizar</button></div></div> : null}
          {children}
        </main>
      </div>
    </div>
  )
}
