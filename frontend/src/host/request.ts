export interface HostRuntimeConfig {
  apiBaseUrl?: string
  actorId?: string
  actorName?: string
  tenantId?: string
  orgId?: string
  roles?: string[]
  permissions?: string[]
  source?: string
  locale?: string
  requestId?: string
  headers?: Record<string, string>
}

declare global {
  // eslint-disable-next-line no-var
  var __HIFY_HOST__: HostRuntimeConfig | undefined

  interface Window {
    __HIFY_HOST__?: HostRuntimeConfig
  }
}

const DEFAULT_API_BASE_URL = '/api'

export function getHostRuntimeConfig(): HostRuntimeConfig {
  const runtime = (globalThis as typeof globalThis & { __HIFY_HOST__?: HostRuntimeConfig }).__HIFY_HOST__
    || (typeof window !== 'undefined' ? window.__HIFY_HOST__ : undefined)
  if (runtime && typeof runtime === 'object') return runtime
  return hostContextFromLocation()
}

export function resolveApiBaseUrl(config: HostRuntimeConfig = getHostRuntimeConfig()): string {
  const base = String(config.apiBaseUrl || DEFAULT_API_BASE_URL).trim() || DEFAULT_API_BASE_URL
  return base.replace(/\/+$/, '') || DEFAULT_API_BASE_URL
}

export function buildHostHeaders(
  config: HostRuntimeConfig = getHostRuntimeConfig(),
  requestIdFactory: () => string = createRequestId,
): Record<string, string> {
  const headers: Record<string, string> = {}
  assignHeader(headers, 'X-Hify-Actor-Id', config.actorId)
  assignHeader(headers, 'X-Hify-Actor-Name', config.actorName)
  assignHeader(headers, 'X-Hify-Tenant-Id', config.tenantId)
  assignHeader(headers, 'X-Hify-Org-Id', config.orgId)
  assignHeader(headers, 'X-Hify-Roles', config.roles?.join(','))
  assignHeader(headers, 'X-Hify-Permissions', config.permissions?.join(','))
  assignHeader(headers, 'X-Hify-Source', config.source)
  assignHeader(headers, 'X-Hify-Locale', config.locale)
  assignHeader(headers, 'X-Request-Id', config.requestId || requestIdFactory())
  return { ...headers, ...(config.headers || {}) }
}

export function resolveApiUrl(path: string, config: HostRuntimeConfig = getHostRuntimeConfig()): string {
  if (/^https?:\/\//i.test(path)) return path
  const base = resolveApiBaseUrl(config)
  let normalizedPath = path.startsWith('/') ? path : `/${path}`
  if (base.endsWith('/api') && normalizedPath.startsWith('/api/')) {
    normalizedPath = normalizedPath.slice('/api'.length)
  }
  return `${base}${normalizedPath}`
}

export function hostFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const config = getHostRuntimeConfig()
  const headers = {
    ...buildHostHeaders(config),
    ...headersToRecord(init.headers),
  }
  return fetch(resolveApiUrl(path, config), {
    ...init,
    headers,
  })
}

function assignHeader(headers: Record<string, string>, key: string, value: string | undefined) {
  const normalized = String(value || '').trim()
  if (normalized) headers[key] = normalized
}

function headersToRecord(headers: HeadersInit | undefined): Record<string, string> {
  if (!headers) return {}
  if (isHeaders(headers)) {
    return Object.fromEntries(headers.entries())
  }
  if (Array.isArray(headers)) return Object.fromEntries(headers)
  return { ...(headers as Record<string, string>) }
}

function isHeaders(headers: HeadersInit): headers is Headers {
  return typeof Headers !== 'undefined' && headers instanceof Headers
}

function createRequestId(): string {
  const cryptoApi = (globalThis as typeof globalThis & { crypto?: Crypto }).crypto
  if (cryptoApi?.randomUUID) return cryptoApi.randomUUID()
  return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function hostContextFromLocation(): HostRuntimeConfig {
  if (typeof window === 'undefined') return {}
  const raw = new URLSearchParams(window.location.search).get('hifyHostContext')
  if (!raw) return {}
  try {
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}
