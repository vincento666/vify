import type { RuntimeOpsRunListQuery, RuntimeOpsRunListResponse } from '@/api/runtimeOps'

export interface RuntimeOpsRunFilters {
  ownerType?: string
  state?: string
  tenantId?: string
  createdFrom?: string
  createdTo?: string
  page?: number
  pageSize?: number
}

export interface RuntimeOpsRunListItem {
  runId: number
  ownerType: string
  ownerTypeLabel: string
  ownerId: number
  ownerLabel: string
  status: string
  state: string
  stateLabel: string
  tenantId: string
  queueState: string
  elapsedMs: number
  createdAt: string
  updatedAt: string
  finishedAt: string
}

export interface RuntimeOpsRunListViewModel {
  items: RuntimeOpsRunListItem[]
  total: number
}

export const runtimeOpsOwnerTypeOptions = [
  { value: 'WORKFLOW', label: 'Workflow' },
  { value: 'CHATFLOW', label: 'Chatflow' },
  { value: 'CUSTOMER_ASSISTANT', label: 'Customer Assistant' },
  { value: 'SOP', label: 'SOP' },
]

export const runtimeOpsStateOptions = [
  { value: 'queued', label: '排队中' },
  { value: 'running', label: '运行中' },
  { value: 'waiting', label: '等待中' },
  { value: 'succeeded', label: '已成功' },
  { value: 'failed', label: '已失败' },
  { value: 'cancelled', label: '已取消' },
]

const ownerTypeLabelMap = new Map(runtimeOpsOwnerTypeOptions.map((item) => [item.value, item.label]))
const stateLabelMap = new Map(runtimeOpsStateOptions.map((item) => [item.value, item.label]))

export function buildRuntimeOpsRunListQuery(filters: RuntimeOpsRunFilters): RuntimeOpsRunListQuery {
  const query: RuntimeOpsRunListQuery = {
    page: filters.page || 1,
    pageSize: filters.pageSize || 20,
  }
  assignString(query, 'ownerType', filters.ownerType)
  assignString(query, 'state', filters.state)
  assignString(query, 'tenantId', filters.tenantId)
  assignString(query, 'createdFrom', filters.createdFrom)
  assignString(query, 'createdTo', filters.createdTo)
  return query
}

export function normalizeRuntimeOpsRunList(response: RuntimeOpsRunListResponse): RuntimeOpsRunListViewModel {
  return {
    total: Number(response.total || 0),
    items: (response.list || []).map(normalizeRuntimeOpsRun),
  }
}

export function normalizeRuntimeOpsRun(row: Record<string, any>): RuntimeOpsRunListItem {
  const ownerType = String(row.ownerType || '').toUpperCase()
  const state = String(row.state || '').toLowerCase()
  const ownerId = Number(row.ownerId || 0)
  return {
    runId: Number(row.runId || 0),
    ownerType,
    ownerTypeLabel: ownerTypeLabelMap.get(ownerType) || ownerType || 'Runtime',
    ownerId,
    ownerLabel: String(row.ownerName || row.ownerLabel || `${ownerType} #${ownerId}`),
    status: String(row.status || '').toUpperCase(),
    state,
    stateLabel: stateLabelMap.get(state) || state,
    tenantId: String(row.tenantId || 'local'),
    queueState: String(row.queueState || ''),
    elapsedMs: Number(row.elapsedMs || 0),
    createdAt: String(row.createdAt || ''),
    updatedAt: String(row.updatedAt || ''),
    finishedAt: String(row.finishedAt || ''),
  }
}

function assignString(query: RuntimeOpsRunListQuery, key: keyof RuntimeOpsRunListQuery, value: unknown) {
  const normalized = String(value || '').trim()
  if (normalized) {
    ;(query[key] as string) = normalized
  }
}
