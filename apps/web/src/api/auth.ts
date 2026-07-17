import { apiFetch, toJsonBody } from './client'

export interface OrganizationSummary {
  id: string
  name: string
  slug?: string
}

export interface Membership {
  organization: OrganizationSummary
  role: string
  permissions: string[]
  active: boolean
}

export interface MeResponse {
  user: {
    id: string
    email: string
    full_name?: string | null
    platform_role?: 'platform_admin' | 'platform_support' | 'platform_owner' | string | null
  }
  memberships: Membership[]
  active_organization: OrganizationSummary | null
  active_permissions: string[]
}

export interface LoginResponse {
  tokens: {
    access_token: string
    access_token_expires_in: number
    token_type?: string
  }
  me: MeResponse
  user: string
}

export interface LoginInput {
  email: string
  password: string
}

export function login(payload: LoginInput) {
  return apiFetch<LoginResponse>('/auth/login', {
    method: 'POST',
    body: toJsonBody({ email: payload.email, password: payload.password }),
  })
}

export function me() {
  return apiFetch<MeResponse>('/auth/me')
}

export function refreshSession() {
  return apiFetch<{ tokens: LoginResponse['tokens'] }>('/auth/refresh', { method: 'POST' })
}

export function logout() {
  return apiFetch<{ status: string }>('/auth/logout', { method: 'POST' })
}
