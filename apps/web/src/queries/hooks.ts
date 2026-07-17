import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { login, me } from '../api/auth'
import { acknowledgeIncident, dismissIncident, getIncident, getIncidentAuditLog, listIncidents, resolveIncident } from '../api/incidents'
import { getEvidenceDownloadUrl, listEvidence } from '../api/evidence'
import { createInvite, listInvites, resendInvite, revokeInvite } from '../api/invites'
import { deactivateMember, listMembers, updateMember } from '../api/members'
import { createOperationCamera, createOperationSite, createOperationZone, deleteOperationCamera, deleteOperationSite, deleteOperationZone, getOperationsCatalog, updateOperationCamera, updateOperationSite, updateOperationZone } from '../api/operations'
import { listEdgeWorkers } from '../api/edgeWorkers'
import { queryKeys } from '../api/queryKeys'

export function useCurrentUser(enabled = true) { return useQuery({ queryKey: queryKeys.currentUser, queryFn: me, enabled, retry: false }) }
export function useIncidents(orgId: string | null, filters: Parameters<typeof listIncidents>[1] = {}, enabled = true) { return useQuery({ queryKey: orgId ? queryKeys.incidents(orgId, filters) : ['incidents', 'none'] as const, queryFn: () => listIncidents(orgId!, filters), enabled: enabled && !!orgId, staleTime: 10_000 }) }
export function useIncidentDetail(orgId: string | null, incidentId: string | null, enabled = true) { return useQuery({ queryKey: orgId && incidentId ? queryKeys.incidentDetail(orgId, incidentId) : ['incident-detail', 'none'] as const, queryFn: () => getIncident(orgId!, incidentId!), enabled: enabled && !!orgId && !!incidentId, staleTime: 10_000 }) }
export function useIncidentAudit(orgId: string | null, incidentId: string | null, enabled = true) { return useQuery({ queryKey: orgId && incidentId ? queryKeys.incidentAudit(orgId, incidentId) : ['incident-audit', 'none'] as const, queryFn: () => getIncidentAuditLog(orgId!, incidentId!), enabled: enabled && !!orgId && !!incidentId, staleTime: 10_000 }) }
export function useEvidence(orgId: string | null, incidentId: string | null, enabled = true) { return useQuery({ queryKey: orgId && incidentId ? queryKeys.evidence(orgId, incidentId) : ['evidence', 'none'] as const, queryFn: () => listEvidence(orgId!, incidentId!), enabled: enabled && !!orgId && !!incidentId, staleTime: 10_000 }) }
export function useOperationsCatalog(orgId: string | null, enabled = true) { return useQuery({ queryKey: orgId ? queryKeys.operationsCatalog(orgId) : ['operations-catalog', 'none'] as const, queryFn: () => getOperationsCatalog(orgId!), enabled: enabled && !!orgId, staleTime: 30_000 }) }
export function useInvites(orgId: string | null, enabled = true) { return useQuery({ queryKey: orgId ? queryKeys.invites(orgId) : ['invites', 'none'] as const, queryFn: () => listInvites(orgId!), enabled: enabled && !!orgId, staleTime: 10_000 }) }
export function useMembers(orgId: string | null, enabled = true) { return useQuery({ queryKey: orgId ? queryKeys.members(orgId) : ['members', 'none'] as const, queryFn: () => listMembers(orgId!), enabled: enabled && !!orgId, staleTime: 10_000 }) }

export function useEdgeWorkers(orgId: string | null, enabled = true) {
  // Telemetria muda a cada heartbeat (60s): 30s de staleTime mantém a aba Workers viva
  // sem marretar a API.
  return useQuery({ queryKey: orgId ? ['edge-workers', orgId] as const : ['edge-workers', 'none'] as const, queryFn: () => listEdgeWorkers(orgId!), enabled: enabled && !!orgId, staleTime: 30_000, refetchInterval: 60_000 })
}

export function useOperationMutations(orgId: string | null) {
  const qc = useQueryClient()
  const invalidate = async () => { if (orgId) await qc.invalidateQueries({ queryKey: queryKeys.operationsCatalog(orgId) }) }
  return {
    createSite: useMutation({ mutationFn: (payload: Parameters<typeof createOperationSite>[1]) => createOperationSite(orgId!, payload), onSuccess: () => void invalidate() }),
    createCamera: useMutation({ mutationFn: (payload: Parameters<typeof createOperationCamera>[1]) => createOperationCamera(orgId!, payload), onSuccess: () => void invalidate() }),
    createZone: useMutation({ mutationFn: (payload: Parameters<typeof createOperationZone>[1]) => createOperationZone(orgId!, payload), onSuccess: () => void invalidate() }),
    updateSite: useMutation({ mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateOperationSite>[2] }) => updateOperationSite(orgId!, id, payload), onSuccess: () => void invalidate() }),
    updateCamera: useMutation({ mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateOperationCamera>[2] }) => updateOperationCamera(orgId!, id, payload), onSuccess: () => void invalidate() }),
    updateZone: useMutation({ mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateOperationZone>[2] }) => updateOperationZone(orgId!, id, payload), onSuccess: () => void invalidate() }),
    deleteSite: useMutation({ mutationFn: (id: string) => deleteOperationSite(orgId!, id), onSuccess: () => void invalidate() }),
    deleteCamera: useMutation({ mutationFn: (id: string) => deleteOperationCamera(orgId!, id), onSuccess: () => void invalidate() }),
    deleteZone: useMutation({ mutationFn: (id: string) => deleteOperationZone(orgId!, id), onSuccess: () => void invalidate() }),
  }
}

export function useMemberActions(orgId: string | null) {
  const qc = useQueryClient()
  const invalidate = async () => { if (!orgId) return; await Promise.all([qc.invalidateQueries({ queryKey: queryKeys.members(orgId) }), qc.invalidateQueries({ queryKey: queryKeys.currentUser })]) }
  return {
    update: useMutation({ mutationFn: (payload: { userId: string; role?: string; active?: boolean }) => updateMember(orgId!, payload.userId, { role: payload.role, active: payload.active }), onSuccess: () => void invalidate() }),
    deactivate: useMutation({ mutationFn: (userId: string) => deactivateMember(orgId!, userId), onSuccess: () => void invalidate() }),
  }
}

export function useIncidentActions(orgId: string | null) {
  const qc = useQueryClient()
  const invalidate = async (incidentId?: string) => { if (!orgId) return; await Promise.all([qc.invalidateQueries({ queryKey: ['incidents', orgId] }), incidentId ? qc.invalidateQueries({ queryKey: queryKeys.incidentDetail(orgId, incidentId) }) : Promise.resolve(), incidentId ? qc.invalidateQueries({ queryKey: queryKeys.incidentAudit(orgId, incidentId) }) : Promise.resolve(), incidentId ? qc.invalidateQueries({ queryKey: queryKeys.evidence(orgId, incidentId) }) : Promise.resolve()]) }
  return {
    acknowledge: useMutation({ mutationFn: ({ incidentId }: { incidentId: string }) => acknowledgeIncident(orgId!, incidentId), onSuccess: (_data: unknown, vars: { incidentId: string }) => void invalidate(vars.incidentId) }),
    resolve: useMutation({ mutationFn: ({ incidentId }: { incidentId: string }) => resolveIncident(orgId!, incidentId), onSuccess: (_data: unknown, vars: { incidentId: string }) => void invalidate(vars.incidentId) }),
    dismiss: useMutation({ mutationFn: ({ incidentId }: { incidentId: string }) => dismissIncident(orgId!, incidentId), onSuccess: (_data: unknown, vars: { incidentId: string }) => void invalidate(vars.incidentId) }),
  }
}

export function useEvidenceDownload() { return useMutation({ mutationFn: ({ orgId, incidentId, fileId }: { orgId: string; incidentId: string; fileId: string }) => getEvidenceDownloadUrl(orgId, incidentId, fileId) }) }
export function useLogin() { return useMutation({ mutationFn: login }) }

export function useInviteActions(orgId: string | null) {
  const qc = useQueryClient()
  const invalidate = async () => { if (orgId) await qc.invalidateQueries({ queryKey: queryKeys.invites(orgId) }) }
  return {
    create: useMutation({ mutationFn: (payload: { email: string; role: string }) => createInvite(orgId!, payload), onSuccess: () => void invalidate() }),
    resend: useMutation({ mutationFn: (inviteId: string) => resendInvite(orgId!, inviteId), onSuccess: () => void invalidate() }),
    revoke: useMutation({ mutationFn: (inviteId: string) => revokeInvite(orgId!, inviteId), onSuccess: () => void invalidate() }),
  }
}
