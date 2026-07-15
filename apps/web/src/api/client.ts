export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '/api/v1').replace(/\/$/, '')

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type JsonValue = Record<string, unknown> | unknown[] | string | number | boolean | null
const csrfCookieName = 'csrf_token'
const csrfHeaderName = 'x-csrf-token'

function joinUrl(path: string) {
  return `${apiBaseUrl}${path.startsWith('/') ? path : `/${path}`}`
}

async function parseResponse(response: Response) {
  const contentType = response.headers.get('content-type') ?? ''
  if (response.status === 204) return null
  if (contentType.includes('application/json')) return response.json()
  return response.text()
}

function extractErrorMessage(body: unknown, fallback: string) {
  if (body && typeof body === 'object') {
    const detail = (body as { detail?: unknown }).detail
    if (typeof detail === 'string' && detail.trim()) return detail
    if (Array.isArray(detail) && detail.length > 0) return fallback
  }
  if (typeof body === 'string' && body.trim()) return body
  return fallback
}

function isUnsafeMethod(method: string | undefined) {
  return !['GET', 'HEAD', 'OPTIONS'].includes((method ?? 'GET').toUpperCase())
}

export function readCookie(name: string) {
  if (typeof document === 'undefined') return null
  const prefix = `${encodeURIComponent(name)}=`
  const item = document.cookie.split('; ').find((cookie) => cookie.startsWith(prefix))
  return item ? decodeURIComponent(item.slice(prefix.length)) : null
}

export function csrfHeader() {
  const token = readCookie(csrfCookieName)
  return token ? { [csrfHeaderName]: token } : {}
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (isUnsafeMethod(init.method) && !headers.has(csrfHeaderName)) {
    const token = readCookie(csrfCookieName)
    if (token) headers.set(csrfHeaderName, token)
  }

  const response = await fetch(joinUrl(path), {
    credentials: 'include',
    ...init,
    headers,
  })

  const body = await parseResponse(response)
  if (!response.ok) {
    throw new ApiError(extractErrorMessage(body, `Falha na API (${response.status})`), response.status)
  }

  return body as T
}

export function isSessionError(error: unknown) {
  return isApiError(error) && (error.status === 401 || error.status === 403)
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

export function toJsonBody(value: JsonValue) {
  return JSON.stringify(value)
}
