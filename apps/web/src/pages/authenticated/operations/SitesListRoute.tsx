import { SitesListPage } from './SitesListPage'
import { useOperations, useOperationsLayout } from './OperationsContext'

/** Rota `/dashboard/operations`. */
export function SitesListRoute() {
  const { operationSites, operationCameras, operationZones, operationRules, ENTITY_STATUS_BADGE, onOpenSite } = useOperations()
  const { openDraft } = useOperationsLayout()

  return (
    <SitesListPage
      sites={operationSites}
      cameras={operationCameras}
      zones={operationZones}
      rules={operationRules}
      statusBadge={ENTITY_STATUS_BADGE}
      onOpenSite={onOpenSite}
      onNewSite={() => openDraft('site')}
    />
  )
}
