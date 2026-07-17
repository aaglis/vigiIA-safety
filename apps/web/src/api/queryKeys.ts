import type { IncidentListParams } from './incidents'

export const queryKeys = {
  health: ['health'] as const,
  readiness: ['readiness'] as const,
  metrics: (hasToken: boolean) => ['metrics', hasToken] as const,
  currentUser: ['current-user'] as const,
  incidents: (orgId: string, filters: IncidentListParams) => ['incidents', orgId, filters] as const,
  incidentDetail: (orgId: string, incidentId: string) => ['incident-detail', orgId, incidentId] as const,
  incidentAudit: (orgId: string, incidentId: string) => ['incident-audit', orgId, incidentId] as const,
  evidence: (orgId: string, incidentId: string) => ['evidence', orgId, incidentId] as const,
  operationsCatalog: (orgId: string) => ['operations-catalog', orgId] as const,
  invites: (orgId: string) => ['invites', orgId] as const,
  members: (orgId: string) => ['members', orgId] as const,
  platformOrganizations: ['platform-organizations'] as const,
  platformAuditLogs: (limit: number, offset: number, action: string) => ['platform-audit-logs', limit, offset, action] as const,
  evidenceRetention: (orgId: string) => ['evidence-retention', orgId] as const,
  evidencePurgePreview: (orgId: string, limit: number, offset: number) => ['evidence-purge-preview', orgId, limit, offset] as const,
  evidenceAuditLogs: (orgId: string, limit: number, offset: number, incidentId: string, fileId: string, action: string) => ['evidence-audit-logs', orgId, limit, offset, incidentId, fileId, action] as const,
} as const
