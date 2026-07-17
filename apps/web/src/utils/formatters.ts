import type { MeResponse } from '../api/auth'
import { ApiError } from '../api/client'

export function formatTimestamp(value: string | null) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}

export function formatClock(value: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' }).format(date)
}

export function formatAgoShort(value: string | null) {
  if (!value) return '—'
  const diff = Date.now() - new Date(value).getTime()
  if (Number.isNaN(diff)) return '—'
  const min = Math.max(0, Math.round(diff / 60000))
  if (min < 1) return 'agora'
  if (min < 60) return `${min} min`
  const hours = Math.floor(min / 60)
  if (hours < 24) return `${hours} h`
  return `${Math.floor(hours / 24)} d`
}

export function formatBytes(size: number) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

export function shortHash(value: string | undefined) {
  if (!value) return '—'
  return value.length > 14 ? `${value.slice(0, 6)}…${value.slice(-6)}` : value
}

export function initialsFrom(value: string) {
  const parts = value.trim().split(/[\s@._-]+/).filter(Boolean)
  if (parts.length === 0) return '—'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

export function readMetadataValue(metadata: Record<string, unknown> | undefined, key: string) {
  if (!metadata) return null
  const value = metadata[key]
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return null
}

export function readMetadataValueFromUnknown(metadata: unknown, key: string) {
  if (!metadata || typeof metadata !== 'object' || Array.isArray(metadata)) return null
  return readMetadataValue(metadata as Record<string, unknown>, key)
}

export function selectOrganization(meResponse: MeResponse) {
  return meResponse.active_organization ?? meResponse.memberships.find((membership) => membership.active)?.organization ?? meResponse.memberships[0]?.organization ?? null
}

export function normalizeApiError(error: unknown) {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return 'Não foi possível conectar à API.'
}
