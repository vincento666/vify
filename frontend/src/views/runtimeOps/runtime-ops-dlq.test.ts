import { describe, expect, it } from 'vitest'

import { normalizeRuntimeOpsDlqList, runtimeOpsDlqActions } from './runtimeOpsDlq'

describe('runtime ops DLQ view model', () => {
  it('normalizes failed jobs and exposes retry ignore resolve actions', () => {
    const normalized = normalizeRuntimeOpsDlqList({
      total: 1,
      list: [
        {
          jobId: 910,
          runId: 810,
          ownerType: 'WORKFLOW',
          ownerId: 15,
          status: 'FAILED',
          attemptCount: 3,
          maxAttempts: 3,
          lastError: 'provider timeout',
          tenantId: 'tenant-dlq',
          updatedAt: '2026-07-04T02:00:00Z',
        },
      ],
    })

    expect(runtimeOpsDlqActions.map((item) => item.value)).toEqual(['retry', 'ignore', 'markResolved'])
    expect(normalized.total).toBe(1)
    expect(normalized.items[0]).toMatchObject({
      jobId: 910,
      runId: 810,
      ownerTypeLabel: 'Workflow',
      attemptLabel: '3 / 3',
      lastError: 'provider timeout',
      statusLabel: '已失败',
    })
  })
})
