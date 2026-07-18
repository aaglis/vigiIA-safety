import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiFetch, isSessionError, readCookie, csrfHeader } from '../client'

describe('api client', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    document.cookie.split(';').forEach((cookie) => {
      const name = cookie.split('=')[0]?.trim()
      if (name) document.cookie = `${name}=; Max-Age=0; path=/`
    })
  })

  it('adds the CSRF header on unsafe methods only', async () => {
    document.cookie = 'csrf_token=test-token'
    const fetchMock = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'content-type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)

    await apiFetch('/things', { method: 'POST', body: JSON.stringify({ name: 'x' }) })
    await apiFetch('/things', { method: 'GET' })

    expect(fetchMock).toHaveBeenCalledTimes(2)
    const postInit = fetchMock.mock.calls[0]?.[1] as RequestInit
    const getInit = fetchMock.mock.calls[1]?.[1] as RequestInit
    expect(postInit.method).toBe('POST')
    expect(postInit.credentials).toBe('include')
    expect(postInit.headers).toBeInstanceOf(Headers)
    expect((postInit.headers as Headers).get('accept')).toBe('application/json')
    expect((postInit.headers as Headers).get('content-type')).toBe('application/json')
    expect((postInit.headers as Headers).get('x-csrf-token')).toBe('test-token')
    expect(getInit.method).toBe('GET')
    expect((getInit.headers as Headers).get('x-csrf-token')).toBeNull()
  })

  it('parses JSON error bodies into ApiError', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => new Response(JSON.stringify({ detail: 'nope' }), { status: 403, headers: { 'content-type': 'application/json' } })))

    await expect(apiFetch('/things')).rejects.toMatchObject({ name: 'ApiError', message: 'nope', status: 403 })
  })

  it('exposes session errors and cookie helpers', () => {
    expect(isSessionError(new ApiError('x', 401))).toBe(true)
    expect(isSessionError(new ApiError('x', 500))).toBe(false)
    expect(readCookie('missing')).toBeNull()
    expect(csrfHeader()).toEqual({})
  })
})
