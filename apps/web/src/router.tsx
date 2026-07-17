import { Outlet, createRootRoute, createRoute, createRouter } from '@tanstack/react-router'
import App from './App'
import { OperationsLayout } from './pages/authenticated/operations/OperationsLayout'
import { SitesListRoute } from './pages/authenticated/operations/SitesListRoute'
import { SiteRoute } from './pages/authenticated/operations/SiteRoute'
import { CameraRoute } from './pages/authenticated/operations/CameraRoute'

const rootRoute = createRootRoute({
  component: Outlet,
})

const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'app',
  component: App,
})

const indexRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/',
  component: App,
})

const loginRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/login',
  component: App,
})

const dashboardRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/dashboard',
  component: App,
})

const dashboardIncidentsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/dashboard/incidents',
  component: App,
})

const dashboardEvidenceRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/dashboard/evidence',
  component: App,
})

// Operações: rotas de verdade. O layout monta cabeçalho/KPIs/modais e cada nível abaixo
// é um componente próprio, que lê `siteId`/`cameraId` da URL via useParams.
const operationsLayoutRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/dashboard/operations',
  component: OperationsLayout,
})

const operationsSitesRoute = createRoute({
  getParentRoute: () => operationsLayoutRoute,
  path: '/',
  component: SitesListRoute,
})

const operationsSiteRoute = createRoute({
  getParentRoute: () => operationsLayoutRoute,
  path: 'sites/$siteId',
  component: SiteRoute,
})

const operationsCameraRoute = createRoute({
  getParentRoute: () => operationsLayoutRoute,
  path: 'sites/$siteId/cameras/$cameraId',
  component: CameraRoute,
})

const dashboardOrganizationsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/dashboard/organizations',
  component: App,
})

const dashboardUsersRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/dashboard/users',
  component: App,
})

const dashboardAuditRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/dashboard/audit',
  component: App,
})

const dashboardSettingsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: '/dashboard/settings',
  component: App,
})

const routeTree = rootRoute.addChildren([
  appRoute.addChildren([
    indexRoute,
    loginRoute,
    dashboardRoute,
    dashboardIncidentsRoute,
    dashboardEvidenceRoute,
    operationsLayoutRoute.addChildren([operationsSitesRoute, operationsSiteRoute, operationsCameraRoute]),
    dashboardOrganizationsRoute,
    dashboardUsersRoute,
    dashboardAuditRoute,
    dashboardSettingsRoute,
  ]),
])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
