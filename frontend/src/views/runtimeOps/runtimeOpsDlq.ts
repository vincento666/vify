import type { RuntimeOpsJobListResponse } from '@/api/runtimeOps'

import {
  normalizeRuntimeOpsJobList,
  type RuntimeOpsJobListItem,
  type RuntimeOpsJobListViewModel,
} from './runtimeOpsJobs'

export interface RuntimeOpsDlqAction {
  value: 'retry' | 'ignore' | 'markResolved'
  label: string
}

export interface RuntimeOpsDlqListItem extends RuntimeOpsJobListItem {
  canRetry: boolean
  canIgnore: boolean
  canMarkResolved: boolean
}

export interface RuntimeOpsDlqListViewModel {
  items: RuntimeOpsDlqListItem[]
  total: number
}

export const runtimeOpsDlqActions: RuntimeOpsDlqAction[] = [
  { value: 'retry', label: 'Retry' },
  { value: 'ignore', label: 'Ignore' },
  { value: 'markResolved', label: 'Mark resolved' },
]

export function normalizeRuntimeOpsDlqList(response: RuntimeOpsJobListResponse): RuntimeOpsDlqListViewModel {
  const normalized: RuntimeOpsJobListViewModel = normalizeRuntimeOpsJobList(response)
  return {
    total: normalized.total,
    items: normalized.items.map((item) => ({
      ...item,
      canRetry: item.status === 'FAILED',
      canIgnore: item.status === 'FAILED',
      canMarkResolved: item.status === 'FAILED',
    })),
  }
}
