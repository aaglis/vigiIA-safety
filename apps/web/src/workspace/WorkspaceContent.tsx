import type { ComponentProps } from 'react'
import { AuditPage } from '../pages/authenticated/AuditPage'
import { EvidenceWorkspace } from './EvidenceWorkspace'
import { IncidentWorkspace } from './IncidentWorkspace'
import { OperationsShell } from './OperationsShell'
import { OverviewPage } from '../pages/authenticated/OverviewPage'
import { OrganizationsPage } from '../pages/authenticated/OrganizationsPage'
import { SettingsPage } from '../pages/authenticated/SettingsPage'
import { UsersPage } from '../pages/authenticated/UsersPage'

type WorkspaceContentProps = {
  workspaceSection: 'dashboard' | 'incidents' | 'evidence' | 'operations' | 'audit' | 'organizations' | 'users' | 'settings'
  overview: ComponentProps<typeof OverviewPage>
  incidents: ComponentProps<typeof IncidentWorkspace>
  evidence: ComponentProps<typeof EvidenceWorkspace>
  operations: ComponentProps<typeof OperationsShell>
  audit: ComponentProps<typeof AuditPage>
  organizations: ComponentProps<typeof OrganizationsPage>
  users: ComponentProps<typeof UsersPage>
  settings: ComponentProps<typeof SettingsPage>
}

export function WorkspaceContent({ workspaceSection, overview, incidents, evidence, operations, audit, organizations, users, settings }: WorkspaceContentProps) {
  switch (workspaceSection) {
    case 'dashboard': return <OverviewPage {...overview} />
    case 'incidents': return <IncidentWorkspace {...incidents} />
    case 'evidence': return <EvidenceWorkspace {...evidence} />
    case 'operations': return <OperationsShell {...operations} />
    case 'audit': return <AuditPage {...audit} />
    case 'organizations': return <OrganizationsPage {...organizations} />
    case 'users': return <UsersPage {...users} />
    case 'settings': return <SettingsPage {...settings} />
    default: return null
  }
}
