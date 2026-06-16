import { describe, expect, it } from 'vitest'

import { summarizeWorkflowRunDebug } from './workflowRunDebug'
import {
  applyRuntimeV2EventsToDebugDetail,
  applyRuntimeV2NodesToDebugDetail,
  createRuntimeV2DebugDetail,
  resolveRunLogAction,
} from './runtimeV2Debug'

describe('runtime v2 canvas debug projection', () => {
  it('routes a completed runtime v2 trial log button to the v2 run detail query', () => {
    expect(resolveRunLogAction(701, 'v2')).toEqual({
      shouldOpenRunDetail: true,
      runtimeQuery: { runtime: 'v2' },
    })
  })

  it('keeps the log drawer local when no run has been created yet', () => {
    expect(resolveRunLogAction(0, 'v2')).toEqual({
      shouldOpenRunDetail: false,
      runtimeQuery: {},
    })
  })

  it('updates node status from live events and polled nodes, then makes failure visible', () => {
    const started = createRuntimeV2DebugDetail({
      runId: 701,
      ownerType: 'WORKFLOW',
      ownerId: 12,
      status: 'RUNNING',
      eventStreamRef: '/api/v1/runtime-runs/701/events/stream?afterSequence=0',
      eventsRef: '/api/v1/runtime-runs/701/events',
      nodesRef: '/api/v1/runtime-runs/701/nodes',
      resultRef: '/api/v1/runtime-runs/701/result',
    })

    const running = applyRuntimeV2EventsToDebugDetail(started, [
      {
        id: 1,
        runId: 701,
        sequence: 1,
        type: 'node_status_changed',
        nodeId: 'message_1',
        payload: { nodeType: 'MESSAGE', nodeRunId: 31, status: 'RUNNING' },
      },
    ])

    expect(running.nodeDetails?.find((node) => node.nodeKey === 'message_1')?.status).toBe('RUNNING')

    const completed = applyRuntimeV2NodesToDebugDetail(running, [
      {
        id: 31,
        runId: 701,
        nodeKey: 'message_1',
        nodeType: 'MESSAGE',
        status: 'COMPLETED',
        outputs: { answer: 'hello' },
      },
    ])

    expect(completed.nodeDetails?.find((node) => node.nodeKey === 'message_1')).toMatchObject({
      id: 31,
      nodeKey: 'message_1',
      nodeType: 'MESSAGE',
      status: 'COMPLETED',
      outputs: { answer: 'hello' },
    })

    const failed = applyRuntimeV2EventsToDebugDetail(completed, [
      {
        id: 2,
        runId: 701,
        sequence: 2,
        type: 'workflow_node_failed',
        nodeId: 'api_1',
        payload: { nodeType: 'API_CALL', nodeRunId: 32, error: 'timeout' },
        observability: { nodeState: 'FAILED' },
      },
    ])

    expect(failed.status).toBe('FAILED')
    expect(failed.error).toBe('timeout')
    expect(failed.nodeDetails?.find((node) => node.nodeKey === 'api_1')).toMatchObject({
      id: 32,
      nodeKey: 'api_1',
      nodeType: 'API_CALL',
      status: 'FAILED',
      error: 'timeout',
      errorSummary: 'timeout',
    })
    expect(summarizeWorkflowRunDebug(failed).statusLabel).toBe('FAILED')
  })

  it('projects workflow run cancellation events into a terminal cancelled state', () => {
    const started = createRuntimeV2DebugDetail({
      runId: 802,
      ownerType: 'CHATFLOW',
      ownerId: 33,
      status: 'RUNNING',
    })

    const cancelled = applyRuntimeV2EventsToDebugDetail(started, [
      {
        id: 7,
        runId: 802,
        sequence: 7,
        type: 'workflow_run_cancelled',
        payload: {
          previousStatus: 'RUNNING',
          reason: 'cancelled by operator',
        },
      },
    ])

    expect(cancelled.status).toBe('CANCELLED')
    expect(cancelled.error).toBe('')
    expect(summarizeWorkflowRunDebug(cancelled).statusLabel).toBe('CANCELLED')
  })
})
