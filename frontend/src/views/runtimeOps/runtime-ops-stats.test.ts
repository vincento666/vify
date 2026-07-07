import { describe, expect, it } from 'vitest'

import { buildRuntimeOpsStatsView } from './runtimeOpsStats'

describe('runtime ops stats view model', () => {
  it('aggregates provider api tool calls and failure retry evidence', () => {
    const view = buildRuntimeOpsStatsView({
      nodes: [
        { nodeKey: 'llm_1', nodeType: 'LLM', status: 'FAILED' },
        { nodeKey: 'api_1', nodeType: 'API_CALL', status: 'COMPLETED' },
        { nodeKey: 'tool_1', nodeType: 'TOOL_CALL', status: 'COMPLETED' },
      ],
      events: [
        {
          type: 'workflow_node_external_call_failed',
          nodeId: 'llm_1',
          payload: {
            callType: 'LLM',
            providerKey: 'llm:gpt-4o',
            errorKind: 'provider_timeout',
            message: 'provider timeout',
            attempts: 3,
            retryCount: 2,
            breakerOpen: true,
          },
        },
        {
          type: 'workflow_node_external_call_failed',
          nodeId: 'api_1',
          payload: {
            callType: 'API_CALL',
            providerKey: 'api:orders',
            errorKind: 'provider_error',
            message: 'orders 500',
            attempts: 2,
            retryCount: 1,
          },
        },
        {
          type: 'workflow_node_completed',
          nodeId: 'tool_1',
          payload: { callType: 'TOOL_CALL', providerKey: 'tool:lookup_order' },
        },
      ],
      jobs: [
        {
          jobId: 990,
          status: 'QUEUED',
          attemptCount: 2,
          maxAttempts: 5,
          nextRetryAt: '2026-07-04T02:00:00Z',
          lastError: 'provider timeout',
        },
      ],
      dlq: [
        {
          jobId: 991,
          status: 'FAILED',
          attemptCount: 5,
          maxAttempts: 5,
          lastError: 'tool exhausted',
        },
      ],
    })

    expect(view.callStats.map((item) => [item.kind, item.total, item.failed, item.retries])).toEqual([
      ['provider', 1, 1, 2],
      ['api', 1, 1, 1],
      ['tool', 1, 0, 0],
    ])
    expect(view.failureItems.map((item) => [item.source, item.target, item.retryLabel, item.message])).toEqual([
      ['event', 'llm:gpt-4o', 'attempts 3, retries 2, breaker open', 'provider_timeout: provider timeout'],
      ['event', 'api:orders', 'attempts 2, retries 1', 'provider_error: orders 500'],
      ['job', 'Job #990', '2 / 5, next 2026-07-04T02:00:00Z', 'provider timeout'],
      ['dlq', 'DLQ #991', '5 / 5', 'tool exhausted'],
    ])
  })
})
