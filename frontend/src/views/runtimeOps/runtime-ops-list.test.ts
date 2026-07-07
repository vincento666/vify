import { describe, expect, it } from 'vitest'

import {
  buildRuntimeOpsRunListQuery,
  normalizeRuntimeOpsRunList,
  runtimeOpsOwnerTypeOptions,
  runtimeOpsStateOptions,
} from './runtimeOpsRuns'

describe('runtime ops run list view model', () => {
  it('builds owner, state, time, tenant, and paging query params', () => {
    expect(
      buildRuntimeOpsRunListQuery({
        ownerType: 'WORKFLOW',
        state: 'running',
        tenantId: 'tenant-a',
        createdFrom: '2026-07-04T00:00:00.000Z',
        createdTo: '2026-07-04T23:59:59.000Z',
        page: 2,
        pageSize: 25,
      }),
    ).toEqual({
      ownerType: 'WORKFLOW',
      state: 'running',
      tenantId: 'tenant-a',
      createdFrom: '2026-07-04T00:00:00.000Z',
      createdTo: '2026-07-04T23:59:59.000Z',
      page: 2,
      pageSize: 25,
    })
  })

  it('normalizes run rows and exposes all required filter options', () => {
    const normalized = normalizeRuntimeOpsRunList({
      total: 1,
      list: [
        {
          runId: 701,
          ownerType: 'WORKFLOW',
          ownerId: 12,
          ownerName: 'Workflow Alpha',
          status: 'RUNNING',
          state: 'running',
          tenantId: 'tenant-a',
          queueState: 'running',
          createdAt: '2026-07-04T01:00:00Z',
          updatedAt: '2026-07-04T01:01:00Z',
        },
      ],
    })

    expect(runtimeOpsOwnerTypeOptions.map((item) => item.value)).toEqual([
      'WORKFLOW',
      'CHATFLOW',
      'CUSTOMER_ASSISTANT',
      'SOP',
    ])
    expect(runtimeOpsStateOptions.map((item) => item.value)).toEqual([
      'queued',
      'running',
      'waiting',
      'succeeded',
      'failed',
      'cancelled',
    ])
    expect(normalized.total).toBe(1)
    expect(normalized.items[0]).toMatchObject({
      runId: 701,
      ownerLabel: 'Workflow Alpha',
      ownerTypeLabel: 'Workflow',
      stateLabel: '运行中',
      tenantId: 'tenant-a',
      queueState: 'running',
    })
  })
})
