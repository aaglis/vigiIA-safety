import type { ComponentProps } from 'react'
import { IncidentsPage } from '../pages/authenticated/IncidentsPage'

type IncidentWorkspaceProps = ComponentProps<typeof IncidentsPage>

export function IncidentWorkspace(props: IncidentWorkspaceProps) {
  return <IncidentsPage {...props} />
}
