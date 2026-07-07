import { describe, expect, it } from 'vitest'

import {
  buildRuntimeOpsJobListQuery,
  normalizeRuntimeOpsJobList,
  runtimeOpsJobStatusOptions,
} from './runtimeOpsJobs'

describe('runtime ops job queue view model', () => {
  it('builds job queue query params', () => {
    expect(
      buildRuntimeOpsJobListQuery({
        ownerType: 'WORKFLOW',
        status: 'RUNNING',
        tenantId: 'tenant-a',
        page: 2,
        pageSize: 25,
      }),
    ).toEqual({
      ownerType: 'WORKFLOW',
      status: 'RUNNING',
      tenantId: 'tenant-a',
      page: 2,
      pageSize: 25,
    })
  })

  it('normalizes lease, heartbeat, attempt, and next retry fields', () => {
    const normalized = normalizeRuntimeOpsJobList({
      total: 2,
      list: [
        {
          jobId: 901,
          runId: 701,
          ownerType: 'WORKFLOW',
          ownerId: 12,
          status: 'RUNNING',
          leaseOwner: 'worker-live',
          lastHeartbeatAt: '2026-07-04T01:02:03Z',
          leaseExpiresAt: '2026-07-04T01:03:03Z',
          attemptCount: 2,
          maxAttempts: 5,
          tenantId: 'tenant-a',
        },
        {
          jobId: 902,
          runId: 702,
          ownerType: 'CHATFLOW',
          ownerId: 13,
          status: 'QUEUED',
          attemptCount: 1,
          maxAttempts: 3,
          availableAt: '2026-07-04T01:05:00Z',
          nextRetryAt: '2026-07-04T01:05:00Z',
          lastError: 'provider timeout',
          tenantId: 'tenant-b',
        },
      ],
    })

    expect(runtimeOpsJobStatusOptions.map((item) => item.value)).toEqual([
      'QUEUED',
      'RUNNING',
      'COMPLETED',
      'FAILED',
      'CANCELLED',
      'IGNORED',
      'RESOLVED',
    ])
    expect(normalized.total).toBe(2)
    expect(normalized.items[0]).toMatchObject({
      jobId: 901,
      statusLabel: '运行中',
      leaseOwner: 'worker-live',
      heartbeatLabel: '2026-07-04T01:02:03Z',
      attemptLabel: '2 / 5',
      nextRetryLabel: '-',
    })
    expect(normalized.items[1]).toMatchObject({
      jobId: 902,
      statusLabel: '排队中',
      attemptLabel: '1 / 3',
      nextRetryLabel: '2026-07-04T01:05:00Z',
      lastError: 'provider timeout',
    })
  })
})
