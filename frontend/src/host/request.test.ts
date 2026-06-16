import { afterEach, describe, expect, it, vi } from 'vitest'

import { buildHostHeaders, hostFetch, resolveApiBaseUrl } from './request'

describe('host request adapter', () => {
  afterEach(() => {
    delete globalThis.__HIFY_HOST__
    vi.unstubAllGlobals()
  })

  it('builds host context headers from runtime config', () => {
    const headers = buildHostHeaders({
      actorId: 'host-user',
      actorName: 'Host User',
      tenantId: 'tenant-alpha',
      orgId: 'org-main',
      roles: ['builder', 'reviewer'],
      permissions: ['workflow:run', 'evaluation:run'],
      source: 'embedded-shell',
      locale: 'zh-CN',
      headers: { Authorization: 'Bearer host-token' },
    }, () => 'req-fixed')

    expect(headers).toEqual({
      'X-Hify-Actor-Id': 'host-user',
      'X-Hify-Actor-Name': 'Host User',
      'X-Hify-Tenant-Id': 'tenant-alpha',
      'X-Hify-Org-Id': 'org-main',
      'X-Hify-Roles': 'builder,reviewer',
      'X-Hify-Permissions': 'workflow:run,evaluation:run',
      'X-Hify-Source': 'embedded-shell',
      'X-Hify-Locale': 'zh-CN',
      'X-Request-Id': 'req-fixed',
      Authorization: 'Bearer host-token',
    })
  })

  it('resolves base URL from runtime config and sends headers through fetch', async () => {
    globalThis.__HIFY_HOST__ = {
      apiBaseUrl: 'https://host.example/api/',
      actorId: 'fetch-user',
      tenantId: 'tenant-fetch',
      requestId: 'req-fetch',
    }
    const fetchSpy = vi.fn(async (_url: string, _init?: RequestInit) => new Response('ok'))
    vi.stubGlobal('fetch', fetchSpy)

    expect(resolveApiBaseUrl()).toBe('https://host.example/api')
    await hostFetch('/v1/workflows', { method: 'POST', headers: { 'Content-Type': 'application/json' } })

    expect(fetchSpy).toHaveBeenCalledTimes(1)
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('https://host.example/api/v1/workflows')
    const headers = init.headers as Record<string, string>
    expect(headers['Content-Type']).toBe('application/json')
    expect(headers['X-Hify-Actor-Id']).toBe('fetch-user')
    expect(headers['X-Hify-Tenant-Id']).toBe('tenant-fetch')
    expect(headers['X-Request-Id']).toBe('req-fetch')
  })
})
