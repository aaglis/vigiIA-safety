export type Screen = 'landing' | 'login' | 'dashboard'
export type AppSection = 'dashboard' | 'incidents' | 'evidence' | 'operations' | 'organizations' | 'users' | 'audit' | 'settings'

/** Nível dentro de Operações. A URL é a fonte da verdade — não estado interno da página. */
export type OperationsRoute =
  | { level: 'sites' }
  | { level: 'site'; siteId: string }
  | { level: 'camera'; siteId: string; cameraId: string }

export type ResolvedRoute = {
  screen: Screen
  section: AppSection
  operations?: OperationsRoute
}

type WorkspaceNavItem = { id: AppSection; path: string }

const workspaceNavItems: WorkspaceNavItem[] = [
  { id: 'dashboard', path: '/dashboard' },
  { id: 'incidents', path: '/dashboard/incidents' },
  { id: 'evidence', path: '/dashboard/evidence' },
  { id: 'operations', path: '/dashboard/operations' },
  { id: 'organizations', path: '/dashboard/organizations' },
  { id: 'users', path: '/dashboard/users' },
  { id: 'audit', path: '/dashboard/audit' },
  { id: 'settings', path: '/dashboard/settings' },
]

const workspacePathById = Object.fromEntries(workspaceNavItems.map((item) => [item.id, item.path])) as Record<AppSection, string>

export function normalizePathname(pathname: string) {
  if (!pathname) return '/'
  if (pathname.length > 1 && pathname.endsWith('/')) return pathname.replace(/\/+$/, '')
  return pathname
}

const OPERATIONS_BASE = '/dashboard/operations'

function resolveOperations(path: string): OperationsRoute | null {
  if (path === OPERATIONS_BASE) return { level: 'sites' }
  if (!path.startsWith(`${OPERATIONS_BASE}/`)) return null
  const segments = path.slice(OPERATIONS_BASE.length + 1).split('/').filter(Boolean)
  // sites/:siteId[/cameras/:cameraId]
  if (segments[0] !== 'sites' || !segments[1]) return { level: 'sites' }
  const siteId = decodeURIComponent(segments[1])
  if (segments[2] === 'cameras' && segments[3]) {
    return { level: 'camera', siteId, cameraId: decodeURIComponent(segments[3]) }
  }
  return { level: 'site', siteId }
}

export function resolveRoute(pathname: string): ResolvedRoute {
  const path = normalizePathname(pathname)
  if (path === '/' || path === '/landing') return { screen: 'landing', section: 'dashboard' }
  if (path === '/login') return { screen: 'login', section: 'dashboard' }

  const operations = resolveOperations(path)
  if (operations) return { screen: 'dashboard', section: 'operations', operations }

  const workspaceItem = workspaceNavItems.find((item) => item.path === path)
  if (workspaceItem) return { screen: 'dashboard', section: workspaceItem.id }
  if (path.startsWith('/dashboard')) return { screen: 'dashboard', section: 'dashboard' }

  return { screen: 'landing', section: 'dashboard' }
}

export function routeForSection(section: AppSection) {
  return workspacePathById[section] ?? '/dashboard'
}

export function routeForSite(siteId: string) {
  return `${OPERATIONS_BASE}/sites/${encodeURIComponent(siteId)}`
}

export function routeForCamera(siteId: string, cameraId: string) {
  return `${routeForSite(siteId)}/cameras/${encodeURIComponent(cameraId)}`
}
