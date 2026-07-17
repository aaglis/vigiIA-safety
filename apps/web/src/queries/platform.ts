import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { getHealth, getMetrics, getReadiness } from '../api/health'
import { listEvidenceAuditLogs, getEvidenceRetentionPolicy, previewEvidencePurge, purgeExpiredEvidence, updateEvidenceRetentionPolicy } from '../api/evidenceAdmin'
import { createPlatformOrganization, listPlatformAuditLogs, listPlatformOrganizations, reactivatePlatformOrganization, suspendPlatformOrganization } from '../api/platform'
import { queryKeys } from '../api/queryKeys'

export function useHealth(enabled = true) { return useQuery({ queryKey: queryKeys.health, queryFn: getHealth, enabled }) }
export function useReadiness(enabled = true) { return useQuery({ queryKey: queryKeys.readiness, queryFn: getReadiness, enabled }) }
export function useMetrics(metricsToken?: string, enabled = true) { return useQuery({ queryKey: queryKeys.metrics(!!metricsToken), queryFn: () => getMetrics(metricsToken), enabled }) }
export function useEvidenceRetention(organizationId: string | null, enabled = true) { return useQuery({ queryKey: organizationId ? queryKeys.evidenceRetention(organizationId) : ['evidence-retention', 'none'] as const, queryFn: () => getEvidenceRetentionPolicy(organizationId!), enabled: enabled && !!organizationId }) }
export function useEvidencePurgePreview(organizationId: string | null, enabled = true) { return useQuery({ queryKey: organizationId ? queryKeys.evidencePurgePreview(organizationId, 25, 0) : ['evidence-purge-preview', 'none'] as const, queryFn: () => previewEvidencePurge(organizationId!, { limit: 25, offset: 0 }), enabled: enabled && !!organizationId }) }
export function usePlatformAuditLogs(params: { limit?: number; offset?: number; action?: string } = {}, enabled = true) { return useQuery({ queryKey: queryKeys.platformAuditLogs(params.limit ?? 50, params.offset ?? 0, params.action ?? ''), queryFn: () => listPlatformAuditLogs(params), enabled }) }
export function useEvidenceAuditLogs(organizationId: string | null, params: { limit?: number; offset?: number; incident_id?: string; file_id?: string; action?: string } = {}, enabled = true) { return useQuery({ queryKey: organizationId ? queryKeys.evidenceAuditLogs(organizationId, params.limit ?? 50, params.offset ?? 0, params.incident_id ?? '', params.file_id ?? '', params.action ?? '') : ['evidence-audit-logs', 'none'] as const, queryFn: () => listEvidenceAuditLogs(organizationId!, params), enabled: enabled && !!organizationId }) }
export function usePlatformOrganizations(enabled = true) { return useQuery({ queryKey: queryKeys.platformOrganizations, queryFn: listPlatformOrganizations, enabled }) }

export function usePlatformAdminMutations() {
  const qc = useQueryClient()
  const invalidate = async () => { await Promise.all([qc.invalidateQueries({ queryKey: queryKeys.platformOrganizations }), qc.invalidateQueries({ queryKey: queryKeys.platformAuditLogs(50, 0, '') })]) }
  return {
    createOrganization: useMutation({ mutationFn: createPlatformOrganization, onSuccess: () => void invalidate() }),
    suspendOrganization: useMutation({ mutationFn: suspendPlatformOrganization, onSuccess: () => void invalidate() }),
    reactivateOrganization: useMutation({ mutationFn: reactivatePlatformOrganization, onSuccess: () => void invalidate() }),
  }
}

export function useEvidenceAdminMutations(organizationId: string | null) {
  const qc = useQueryClient()
  const invalidate = async () => { if (!organizationId) return; await Promise.all([qc.invalidateQueries({ queryKey: queryKeys.evidenceRetention(organizationId) }), qc.invalidateQueries({ queryKey: queryKeys.evidencePurgePreview(organizationId, 25, 0) }), qc.invalidateQueries({ queryKey: queryKeys.evidenceAuditLogs(organizationId, 50, 0, '', '', '') })]) }
  return {
    updateRetention: useMutation({ mutationFn: (payload: { metadata_days: number; snapshot_days: number; clip_days: number; audit_log_days: number; reason?: string }) => updateEvidenceRetentionPolicy(organizationId!, payload), onSuccess: () => void invalidate() }),
    purgeExpired: useMutation({ mutationFn: (payload: { confirm: boolean; reason: string }) => purgeExpiredEvidence(organizationId!, payload), onSuccess: () => void invalidate() }),
  }
}
