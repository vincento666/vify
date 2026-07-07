import type { RuntimeOpsJobListQuery, RuntimeOpsJobListResponse } from '@/api/runtimeOps'

export interface RuntimeOpsJobFilters {
  ownerType?: string
  status?: string
  tenantId?: string
  page?: number
  pageSize?: number
}

export interface RuntimeOpsJobListItem {
  jobId: number
  runId: number
  ownerType: string
  ownerTypeLabel: string
  ownerId: number
  status: string
  statusLabel: string
  leaseOwner: string
  lastHeartbeatAt: string
  heartbeatLabel: string
  leaseExpiresAt: string
  attemptCount: number
  maxAttempts: number
  attemptLabel: string
  availableAt: string
  nextRetryAt: string
  nextRetryLabel: string
  lastError: string
  tenantId: string
  updatedAt: string
}

export interface RuntimeOpsJobListViewModel {
  items: RuntimeOpsJobListItem[]
  total: number
}

export const runtimeOpsJobStatusOptions = [
  { value: 'QUEUED', label: '排队中' },
  { value: 'RUNNING', label: '运行中' },
  { value: 'COMPLETED', label: '已完成' },
  { value: 'FAILED', label: '已失败' },
  { value: 'CANCELLED', label: '已取消' },
  { value: 'IGNORED', label: '已忽略' },
  { value: 'RESOLVED', label: '已解决' },
]

const ownerTypeLabelMap = new Map([
  ['WORKFLOW', 'Workflow'],
  ['CHATFLOW', 'Chatflow'],
  ['CUSTOMER_ASSISTANT', 'Customer Assistant'],
  ['SOP', 'SOP'],
])
const statusLabelMap = new Map(runtimeOpsJobStatusOptions.map((item) => [item.value, item.label]))

export function buildRuntimeOpsJobListQuery(filters: RuntimeOpsJobFilters): RuntimeOpsJobListQuery {
  const query: RuntimeOpsJobListQuery = {
    page: filters.page || 1,
    pageSize: filters.pageSize || 20,
  }
  assignString(query, 'ownerType', filters.ownerType)
  assignString(query, 'status', filters.status)
  assignString(query, 'tenantId', filters.tenantId)
  return query
}

export function normalizeRuntimeOpsJobList(response: RuntimeOpsJobListResponse): RuntimeOpsJobListViewModel {
  return {
    total: Number(response.total || 0),
    items: (response.list || []).map(normalizeRuntimeOpsJob),
  }
}

export function normalizeRuntimeOpsJob(row: Record<string, any>): RuntimeOpsJobListItem {
  const ownerType = String(row.ownerType || '').toUpperCase()
  const status = String(row.status || '').toUpperCase()
  const attemptCount = Number(row.attemptCount || 0)
  const maxAttempts = Number(row.maxAttempts || 0)
  const lastHeartbeatAt = String(row.lastHeartbeatAt || '')
  const nextRetryAt = String(row.nextRetryAt || row.availableAt || '')
  return {
    jobId: Number(row.jobId || 0),
    runId: Number(row.runId || 0),
    ownerType,
    ownerTypeLabel: ownerTypeLabelMap.get(ownerType) || ownerType || 'Runtime',
    ownerId: Number(row.ownerId || 0),
    status,
    statusLabel: statusLabelMap.get(status) || status,
    leaseOwner: String(row.leaseOwner || '-'),
    lastHeartbeatAt,
    heartbeatLabel: lastHeartbeatAt || '-',
    leaseExpiresAt: String(row.leaseExpiresAt || ''),
    attemptCount,
    maxAttempts,
    attemptLabel: `${attemptCount} / ${maxAttempts}`,
    availableAt: String(row.availableAt || ''),
    nextRetryAt,
    nextRetryLabel: nextRetryAt || '-',
    lastError: String(row.lastError || ''),
    tenantId: String(row.tenantId || 'local'),
    updatedAt: String(row.updatedAt || ''),
  }
}

function assignString(query: RuntimeOpsJobListQuery, key: keyof RuntimeOpsJobListQuery, value: unknown) {
  const normalized = String(value || '').trim()
  if (normalized) {
    ;(query[key] as string) = normalized
  }
}
