import { apiFetch } from './client'

export interface MemberOrganization {
  id: string
  name: string
  slug: string
}

export interface MemberUser {
  id: string
  email: string
  full_name: string
}

export interface MemberRecord {
  user: MemberUser
  organization: MemberOrganization
  role: string
  permissions: string[]
  active: boolean
}

export interface MemberListResponse { items: MemberRecord[] }
export interface MemberPatchInput { role?: string; active?: boolean }
export interface MemberPatchResponse { member: MemberRecord }

const path = (orgId: string, suffix = '') => `/organizations/${orgId}/members${suffix}`

export function listMembers(orgId: string) { return apiFetch<MemberListResponse>(path(orgId)) }
export function updateMember(orgId: string, userId: string, payload: MemberPatchInput) { return apiFetch<MemberPatchResponse>(path(orgId, `/${userId}`), { method: 'PATCH', body: JSON.stringify(payload) }) }
export function deactivateMember(orgId: string, userId: string) { return apiFetch<MemberPatchResponse>(path(orgId, `/${userId}`), { method: 'DELETE' }) }
