import { describe, expect, it } from 'vitest'

import {
  applyRuntimeV2EventsToDebugDetail,
  createRuntimeV2DebugDetail,
  type RuntimeV2Event,
} from './runtimeV2Debug'

describe('runtime node state store', () => {
  it('maps concurrent DAG events to independent node states with selection metadata', () => {
    const detail = createRuntimeV2DebugDetail({
      runId: 2192,
      ownerType: 'CHATFLOW',
      status: 'RUNNING',
    })
    const events: RuntimeV2Event[] = [
      {
        id: 1,
        runId: 2192,
        sequence: 10,
        type: 'workflow_node_started',
        nodeId: 'vip_message',
        payload: {
          nodeType: 'MESSAGE',
          nodeRunId: 41,
          selectionState: {
            nodeKey: 'vip_message',
            state: 'running',
            selectedUpstreamNodeKeys: ['router'],
            skippedUpstreamNodeKeys: [],
            reason: 'selected branch',
          },
        },
      },
      {
        id: 2,
        runId: 2192,
        sequence: 11,
        type: 'workflow_node_started',
        nodeId: 'audit_log',
        payload: {
          nodeType: 'VARIABLE_ASSIGN',
          nodeRunId: 42,
          selectionState: {
            nodeKey: 'audit_log',
            state: 'running',
            selectedUpstreamNodeKeys: ['router'],
            skippedUpstreamNodeKeys: [],
            reason: 'selected fan-out',
          },
        },
      },
      {
        id: 3,
        runId: 2192,
        sequence: 12,
        type: 'workflow_node_skipped',
        nodeId: 'fallback_message',
        payload: {
          nodeType: 'MESSAGE',
          nodeRunId: 43,
          selectionState: {
            nodeKey: 'fallback_message',
            state: 'skipped',
            selectedUpstreamNodeKeys: [],
            skippedUpstreamNodeKeys: ['router'],
            reason: 'branch not selected',
          },
        },
      },
      {
        id: 4,
        runId: 2192,
        sequence: 13,
        type: 'workflow_node_waiting',
        nodeId: 'approval_question',
        payload: {
          nodeType: 'QUESTION',
          nodeRunId: 44,
          checkpointId: 901,
          selectionState: {
            nodeKey: 'approval_question',
            state: 'waiting',
            selectedUpstreamNodeKeys: ['vip_message', 'audit_log'],
            skippedUpstreamNodeKeys: ['fallback_message'],
            reason: 'implicit join waits only for selected upstreams',
          },
        },
      },
      {
        id: 5,
        runId: 2192,
        sequence: 14,
        type: 'workflow_node_completed',
        nodeId: 'vip_message',
        payload: {
          nodeType: 'MESSAGE',
          nodeRunId: 41,
          outputs: { answer: 'vip ok' },
        },
      },
    ]

    const projected = applyRuntimeV2EventsToDebugDetail(detail, events)
    const byKey = new Map((projected.nodeDetails || []).map((node) => [node.nodeKey, node]))

    expect(byKey.get('vip_message')).toMatchObject({
      id: 41,
      nodeType: 'MESSAGE',
      status: 'COMPLETED',
      outputs: { answer: 'vip ok' },
      selectionState: {
        state: 'running',
        selectedUpstreamNodeKeys: ['router'],
      },
    })
    expect(byKey.get('audit_log')).toMatchObject({
      id: 42,
      nodeType: 'VARIABLE_ASSIGN',
      status: 'RUNNING',
      selectionState: {
        state: 'running',
        selectedUpstreamNodeKeys: ['router'],
      },
    })
    expect(byKey.get('fallback_message')).toMatchObject({
      id: 43,
      nodeType: 'MESSAGE',
      status: 'SKIPPED',
      selectionState: {
        state: 'skipped',
        skippedUpstreamNodeKeys: ['router'],
      },
    })
    expect(byKey.get('approval_question')).toMatchObject({
      id: 44,
      nodeType: 'QUESTION',
      status: 'WAITING',
      selectionState: {
        state: 'waiting',
        selectedUpstreamNodeKeys: ['vip_message', 'audit_log'],
        skippedUpstreamNodeKeys: ['fallback_message'],
      },
    })
  })
})
