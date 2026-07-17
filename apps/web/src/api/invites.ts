import { apiFetch, toJsonBody } from './client'

export type InviteStatus = 'pending' | 'accepted' | 'expired' | 'revoked'

export interface OrganizationInvite {
  id: string
  organization_id: string
  email: string
  role: string
  invited_by_user_id: string
  status: InviteStatus
  expires_at: string
  created_at: string
  updated_at: string
  accepted_at: string | null
  revoked_at: string | null
  accepted_by_user_id: string | null
}

export interface CreateInviteInput {
  email: string
  role: string
}

export function listInvites(organizationId: string) {
  return apiFetch<{ items: OrganizationInvite[] }>(`/organizations/${organizationId}/invites`)
}

export function createInvite(organizationId: string, payload: CreateInviteInput) {
  return apiFetch<{ invite: OrganizationInvite; token: string }>(`/organizations/${organizationId}/invites`, {
    method: 'POST',
    body: toJsonBody({ email: payload.email, role: payload.role }),
  })
}

export function resendInvite(organizationId: string, inviteId: string) {
  return apiFetch<{ token: string }>(`/organizations/${organizationId}/invites/${inviteId}:resend`, { method: 'POST' })
}

export function revokeInvite(organizationId: string, inviteId: string) {
  return apiFetch<{ invite: OrganizationInvite }>(`/organizations/${organizationId}/invites/${inviteId}:revoke`, { method: 'POST' })
}
