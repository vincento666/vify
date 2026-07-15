import { beforeEach, describe, expect, it, vi } from 'vitest'

import { summarizeWorkflowRunDebug } from './workflowRunDebug'
import {
  applyRuntimeV2EventsToDebugDetail,
  applyRuntimeV2NodesToDebugDetail,
  createRuntimeV2DebugDetail,
  openRuntimeV2DebugEventObserver,
  resolveRunLogAction,
  type RuntimeV2Event,
} from './runtimeV2Debug'

class FakeRuntimeEventSource {
  static instances: FakeRuntimeEventSource[] = []

  onmessage: ((event: { data: string }) => void) | null = null
  onerror: ((event: { type: string }) => void) | null = null
  closed = false

  constructor(public readonly url: string) {
    FakeRuntimeEventSource.instances.push(this)
  }

  emit(event: RuntimeV2Event) {
    this.onmessage?.({ data: JSON.stringify(event) })
  }

  disconnect() {
    this.onerror?.({ type: 'error' })
  }

  close() {
    this.closed = true
  }
}

describe('runtime v2 canvas debug projection', () => {
  beforeEach(() => {
    FakeRuntimeEventSource.instances = []
  })

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
        selectionState: {
          nodeKey: 'message_1',
          state: 'completed',
          selectedUpstreamNodeKeys: ['start'],
          skippedUpstreamNodeKeys: [],
          reason: '',
        },
        outputs: { answer: 'hello' },
      },
    ])

    expect(completed.nodeDetails?.find((node) => node.nodeKey === 'message_1')).toMatchObject({
      id: 31,
      nodeKey: 'message_1',
      nodeType: 'MESSAGE',
      status: 'COMPLETED',
      selectionState: {
        nodeKey: 'message_1',
        state: 'completed',
        selectedUpstreamNodeKeys: ['start'],
        skippedUpstreamNodeKeys: [],
        reason: '',
      },
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

  it('projects terminal Runtime V2 output into the chatflow trial result', () => {
    const started = createRuntimeV2DebugDetail({
      runId: 803,
      ownerType: 'CHATFLOW',
      ownerId: 34,
      status: 'RUNNING',
    })

    const completed = applyRuntimeV2EventsToDebugDetail(started, [
      {
        id: 8,
        runId: 803,
        sequence: 8,
        type: 'workflow_run_completed',
        payload: { output: { final: 'live reply' } },
      },
    ])

    expect(completed.status).toBe('SUCCEEDED')
    expect(completed.output).toEqual({ final: 'live reply' })
  })

  it('observes runtime v2 SSE by default and recovers durable events after disconnect without duplicates', async () => {
    let detail = createRuntimeV2DebugDetail({
      runId: 701,
      ownerType: 'WORKFLOW',
      ownerId: 12,
      status: 'RUNNING',
      eventStreamRef: '/api/v1/runtime-runs/701/events/stream?afterSequence=0',
    })
    const appliedSequences: number[] = []
    const listRuntimeV2Events = vi.fn(async () => ({
      list: [
        {
          id: 2,
          runId: 701,
          sequence: 2,
          type: 'workflow_node_failed',
          nodeId: 'api_1',
          payload: { nodeType: 'API_CALL', nodeRunId: 32, error: 'timeout' },
          observability: { nodeState: 'FAILED' },
        },
        {
          id: 4,
          runId: 701,
          sequence: 4,
          type: 'workflow_node_completed',
          nodeId: 'message_1',
          payload: { nodeType: 'MESSAGE', nodeRunId: 31, status: 'COMPLETED' },
        },
        {
          id: 3,
          runId: 701,
          sequence: 3,
          type: 'workflow_node_started',
          nodeId: 'message_1',
          payload: { nodeType: 'MESSAGE', nodeRunId: 31, status: 'RUNNING' },
        },
      ],
      total: 3,
    }))

    const observer = openRuntimeV2DebugEventObserver({
      started: {
        runId: 701,
        eventStreamRef: '/api/v1/runtime-runs/701/events/stream?afterSequence=0',
      },
      eventSourceFactory: (url) => new FakeRuntimeEventSource(url) as unknown as EventSource,
      listRuntimeV2Events,
      onEvents: (events) => {
        appliedSequences.push(...events.map((event) => Number(event.sequence || 0)))
        detail = applyRuntimeV2EventsToDebugDetail(detail, events)
      },
    })

    expect(FakeRuntimeEventSource.instances[0]?.url).toBe('/api/v1/runtime-runs/701/events/stream?afterSequence=0')

    FakeRuntimeEventSource.instances[0].emit({
      id: 1,
      runId: 701,
      sequence: 1,
      type: 'workflow_node_started',
      nodeId: 'start_1',
      payload: { nodeType: 'START', nodeRunId: 30, status: 'RUNNING' },
    })
    FakeRuntimeEventSource.instances[0].emit({
      id: 2,
      runId: 701,
      sequence: 2,
      type: 'workflow_node_failed',
      nodeId: 'api_1',
      payload: { nodeType: 'API_CALL', nodeRunId: 32, error: 'timeout' },
      observability: { nodeState: 'FAILED' },
    })

    expect(observer.lastSequence()).toBe(2)
    expect(detail.status).toBe('FAILED')
    expect(detail.nodeDetails?.find((node) => node.nodeKey === 'api_1')).toMatchObject({
      status: 'FAILED',
      error: 'timeout',
      errorSummary: 'timeout',
    })

    FakeRuntimeEventSource.instances[0].disconnect()

    await vi.waitUntil(() => listRuntimeV2Events.mock.calls.length === 1)
    await vi.waitUntil(() => FakeRuntimeEventSource.instances.length === 2)

    expect(listRuntimeV2Events).toHaveBeenCalledWith(701, { afterSequence: 2 })
    expect(appliedSequences).toEqual([1, 2, 3, 4])
    expect(detail.nodeDetails?.find((node) => node.nodeKey === 'message_1')?.events?.map((event) => event.sequence)).toEqual([3, 4])
    expect(observer.lastSequence()).toBe(4)
    expect(FakeRuntimeEventSource.instances[1]?.url).toBe('/api/v1/runtime-runs/701/events/stream?afterSequence=4')

    observer.close()
    expect(FakeRuntimeEventSource.instances[1]?.closed).toBe(true)
  })

  it('falls back to the canonical runtime v2 SSE URL when no stream ref is provided', () => {
    const observer = openRuntimeV2DebugEventObserver({
      started: { runId: 702 },
      eventSourceFactory: (url) => new FakeRuntimeEventSource(url) as unknown as EventSource,
      listRuntimeV2Events: vi.fn(),
      onEvents: () => {},
    })

    expect(FakeRuntimeEventSource.instances[0]?.url).toBe('/api/v1/runtime-runs/702/events/stream?afterSequence=0')

    observer.close()
  })
})
