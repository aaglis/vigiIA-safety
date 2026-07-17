import { z } from 'zod'

import type { Incident, IncidentStatus } from '../api/incidents'

export type IncidentPeriod = 'all' | '24h' | '7d' | '30d' | 'custom'

export type IncidentFilters = {
  status: IncidentStatus | 'all'
  severity: string
  siteId: string
  cameraId: string
  zoneId: string
  period: IncidentPeriod
  createdFrom: string
  createdTo: string
}

export const defaultIncidentFilters: IncidentFilters = {
  status: 'all',
  severity: 'all',
  siteId: 'all',
  cameraId: 'all',
  zoneId: 'all',
  period: 'all',
  createdFrom: '',
  createdTo: '',
}

const incidentPeriodSchema = z.union([z.literal('all'), z.literal('24h'), z.literal('7d'), z.literal('30d'), z.literal('custom')])
const incidentStatusSchema = z.union([z.literal('all'), z.literal('open'), z.literal('acknowledged'), z.literal('resolved'), z.literal('dismissed')])

const incidentUrlParamsSchema = z.object({
  severity: z.string().optional(),
  siteId: z.string().optional(),
  cameraId: z.string().optional(),
  zoneId: z.string().optional(),
  createdFrom: z.string().optional(),
  createdTo: z.string().optional(),
})

function getPresetRange(period: Exclude<IncidentPeriod, 'all' | 'custom'>) {
  const end = new Date()
  const start = new Date(end)
  if (period === '24h') {
    start.setHours(start.getHours() - 24)
  } else if (period === '7d') {
    start.setDate(start.getDate() - 7)
  } else {
    start.setDate(start.getDate() - 30)
  }
  return { createdFrom: start.toISOString(), createdTo: end.toISOString() }
}

function normalizeCreatedFromValue(value: string) {
  if (!value) return ''
  if (value.includes('T')) {
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? '' : date.toISOString()
  }
  const date = new Date(`${value}T00:00:00`)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString()
}

function normalizeCreatedToValue(value: string) {
  if (!value) return ''
  if (value.includes('T')) {
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? '' : date.toISOString()
  }
  const date = new Date(`${value}T23:59:59.999`)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString()
}

export function incidentMatchesFilters(incident: Incident, filters: IncidentFilters) {
  if (filters.status !== 'all' && incident.status !== filters.status) return false
  if (filters.severity !== 'all' && incident.severity.toLowerCase() !== filters.severity.toLowerCase()) return false
  if (filters.siteId !== 'all' && (incident.site_id ?? '') !== filters.siteId) return false
  if (filters.cameraId !== 'all' && incident.camera_id !== filters.cameraId) return false
  if (filters.zoneId !== 'all' && incident.zone_id !== filters.zoneId) return false

  const createdAt = new Date(incident.created_at).getTime()
  if (filters.createdFrom && createdAt < new Date(filters.createdFrom).getTime()) return false
  if (filters.createdTo && createdAt > new Date(filters.createdTo).getTime()) return false

  return true
}

export function normalizeIncidentFilters(filters: IncidentFilters): IncidentFilters {
  const next = { ...filters }
  if (next.period === 'all') {
    next.createdFrom = ''
    next.createdTo = ''
  } else if (next.period === '24h' || next.period === '7d' || next.period === '30d') {
    const range = getPresetRange(next.period)
    next.createdFrom = range.createdFrom
    next.createdTo = range.createdTo
  } else if (next.period === 'custom') {
    next.createdFrom = next.createdFrom ? normalizeCreatedFromValue(next.createdFrom) : ''
    next.createdTo = next.createdTo ? normalizeCreatedToValue(next.createdTo) : ''
  }
  return next
}

export function readIncidentFiltersFromUrl(): IncidentFilters {
  if (typeof window === 'undefined') return { ...defaultIncidentFilters }
  const params = new URLSearchParams(window.location.search)
  const parsed = incidentUrlParamsSchema.safeParse({
    severity: params.get('severity') ?? undefined,
    siteId: params.get('site_id') ?? undefined,
    cameraId: params.get('camera_id') ?? undefined,
    zoneId: params.get('zone_id') ?? undefined,
    createdFrom: params.get('created_from') ?? undefined,
    createdTo: params.get('created_to') ?? undefined,
  })
  const period = incidentPeriodSchema.catch('all').parse(params.get('period') ?? undefined)
  const status = incidentStatusSchema.catch('all').parse(params.get('status') ?? undefined)

  const next: IncidentFilters = {
    status,
    severity: parsed.success ? parsed.data.severity ?? 'all' : 'all',
    siteId: parsed.success ? parsed.data.siteId ?? 'all' : 'all',
    cameraId: parsed.success ? parsed.data.cameraId ?? 'all' : 'all',
    zoneId: parsed.success ? parsed.data.zoneId ?? 'all' : 'all',
    period,
    createdFrom: parsed.success ? parsed.data.createdFrom ?? '' : '',
    createdTo: parsed.success ? parsed.data.createdTo ?? '' : '',
  }

  if (next.period === 'all' && (next.createdFrom || next.createdTo)) {
    next.period = 'custom'
  }

  return normalizeIncidentFilters(next)
}

export function writeIncidentFiltersToUrl(filters: IncidentFilters) {
  if (typeof window === 'undefined') return
  const params = new URLSearchParams()
  if (filters.status !== 'all') params.set('status', filters.status)
  if (filters.severity !== 'all') params.set('severity', filters.severity)
  if (filters.siteId !== 'all') params.set('site_id', filters.siteId)
  if (filters.cameraId !== 'all') params.set('camera_id', filters.cameraId)
  if (filters.zoneId !== 'all') params.set('zone_id', filters.zoneId)
  if (filters.period !== 'all') params.set('period', filters.period)
  if (filters.createdFrom) params.set('created_from', filters.createdFrom)
  if (filters.createdTo) params.set('created_to', filters.createdTo)

  const search = params.toString()
  const nextUrl = `${window.location.pathname}${search ? `?${search}` : ''}${window.location.hash}`
  window.history.replaceState({}, '', nextUrl)
}

export function formatDateInput(value: string) {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString().slice(0, 10)
}

export function incidentFiltersToParams(filters: IncidentFilters) {
  const next = normalizeIncidentFilters(filters)
  return {
    status: next.status === 'all' ? undefined : next.status,
    severity: next.severity === 'all' ? undefined : next.severity,
    site_id: next.siteId === 'all' ? undefined : next.siteId,
    camera_id: next.cameraId === 'all' ? undefined : next.cameraId,
    zone_id: next.zoneId === 'all' ? undefined : next.zoneId,
    created_from: next.createdFrom || undefined,
    created_to: next.createdTo || undefined,
  }
}
