import { describe, expect, it } from 'vitest'

import { buildRuntimeOpsNodeDetail } from './runtimeOpsNodeDetail'

describe('runtime ops node detail view model', () => {
  it('summarizes node IO, duration, errors, and events while hiding reasoning by default', () => {
    const detail = buildRuntimeOpsNodeDetail({
      node: {
        id: 31,
        nodeKey: 'llm_1',
        nodeType: 'LLM',
        name: 'Draft answer',
        status: 'FAILED',
        elapsedMs: 1234,
        inputs: {
          query: 'refund policy',
          reasoning: 'secret chain of thought input',
        },
        outputs: {
          answer: 'Refund within 7 days',
          toolCalls: [{ name: 'lookup_policy', status: 'failed' }],
          thought: 'secret chain of thought output',
          __debug: { llm: { reasoning: 'hidden provider reasoning' } },
        },
        error: 'provider timeout',
      },
      events: [
        {
          id: 1,
          sequence: 1,
          type: 'workflow_node_started',
          nodeId: 'llm_1',
          payload: { status: 'RUNNING' },
          createdAt: '2026-07-04T01:00:00Z',
        },
        {
          id: 2,
          sequence: 2,
          type: 'workflow_node_failed',
          nodeId: 'llm_1',
          payload: { error: 'provider timeout' },
          createdAt: '2026-07-04T01:00:01Z',
        },
      ],
    })

    expect(detail.durationLabel).toBe('1234ms')
    expect(detail.errorSummary).toBe('provider timeout')
    expect(detail.inputSummary).toContain('refund policy')
    expect(detail.outputSummary).toContain('Refund within 7 days')
    expect(detail.outputSummary).toContain('lookup_policy')
    expect(detail.inputSummary).not.toContain('secret chain')
    expect(detail.outputSummary).not.toContain('secret chain')
    expect(detail.outputSummary).not.toContain('hidden provider reasoning')
    expect(detail.events.map((event) => [event.sequenceLabel, event.eventType, event.detail])).toEqual([
      ['#1', 'workflow_node_started', 'RUNNING'],
      ['#2', 'workflow_node_failed', 'provider timeout'],
    ])
  })
})
