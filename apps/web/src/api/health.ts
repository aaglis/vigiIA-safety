import { apiFetch } from './client'

export interface DependencyCheckResult {
  ok: boolean
  configured: boolean
  sanitized_url?: string | null
  error?: string | null
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  dependencies: {
    database: DependencyCheckResult
    redis: DependencyCheckResult
    minio: DependencyCheckResult
  }
}

export interface MetricsSnapshot {
  requests_total?: Record<string, number>
  request_latency_ms?: Record<string, { count: number; avg: number }>
  [key: string]: unknown
}

export function getHealth() { return apiFetch<HealthResponse>('/health') }
export function getReadiness() { return apiFetch<HealthResponse>('/readiness') }
export function getMetrics(metricsToken?: string) {
  return apiFetch<MetricsSnapshot>('/metrics', { headers: metricsToken ? { 'X-Metrics-Token': metricsToken } : undefined })
}
