import type { ComponentProps } from 'react'
import { EvidenceExplorer } from '../components/evidence/EvidenceExplorer'
import { EvidencePage } from '../pages/authenticated/EvidencePage'

type EvidenceExplorerProps = ComponentProps<typeof EvidenceExplorer>

type EvidenceWorkspaceProps = {
  selectedIncident: ComponentProps<typeof EvidencePage>['selectedIncident']
  activeOrganizationName: string | null
  openWorkspaceSection: ComponentProps<typeof EvidencePage>['openWorkspaceSection']
  explorer: Omit<EvidenceExplorerProps, 'incident' | 'organizationName'>
}

export function EvidenceWorkspace({ selectedIncident, activeOrganizationName, openWorkspaceSection, explorer }: EvidenceWorkspaceProps) {
  return (
    <EvidencePage
      selectedIncident={selectedIncident}
      openWorkspaceSection={openWorkspaceSection}
      evidenceExplorer={selectedIncident ? <EvidenceExplorer incident={selectedIncident} organizationName={activeOrganizationName} {...explorer} /> : null}
    />
  )
}
