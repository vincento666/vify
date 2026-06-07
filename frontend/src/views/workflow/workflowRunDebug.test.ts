import { describe, expect, it } from 'vitest'

import {
  buildWorkflowRunCallTree,
  buildWorkflowRunFlamegraph,
  formatWorkflowNodeEvidence,
  summarizeWorkflowRunDebug,
} from './workflowRunDebug'

describe('workflow run debug view model', () => {
  const detail = {
    runId: 42,
    ownerType: 'WORKFLOW',
    status: 'SUCCEEDED',
    elapsedMs: 38,
    nodeDetails: [
      { nodeKey: 'start', nodeType: 'START', status: 'SUCCEEDED', elapsedMs: 5, outputs: { USER_INPUT: 'hi' } },
      { nodeKey: 'llm', nodeType: 'LLM', status: 'SUCCEEDED', elapsedMs: 30, outputs: { answer: 'hello' } },
      { nodeKey: 'end', nodeType: 'END', status: 'SUCCEEDED', elapsedMs: 3, outputs: { final: 'hello' } },
    ],
  }

  it('summarizes a selected workflow run for the canvas debug dock', () => {
    expect(summarizeWorkflowRunDebug(detail)).toEqual({
      runLabel: 'Run #42',
      statusLabel: 'SUCCEEDED',
      elapsedLabel: '38ms',
      nodeCountLabel: '3 nodes',
    })
  })

  it('builds a call tree from node execution details', () => {
    expect(buildWorkflowRunCallTree(detail).map((node) => `${node.nodeKey}:${node.nodeType}:${node.status}`)).toEqual([
      'llm:LLM:SUCCEEDED',
    ])
  })

  it('builds cumulative flamegraph rows without overlapping durations', () => {
    expect(buildWorkflowRunFlamegraph(detail)).toEqual([
      { detailKey: 'idx:1:llm', nodeKey: 'llm', label: 'LLM llm', startMs: 0, durationMs: 30, status: 'SUCCEEDED' },
    ])
  })

  it('keeps duplicate node executions addressable by execution detail id', () => {
    const duplicateDetail = {
      nodeDetails: [
        { id: 10, nodeKey: 'question_1', nodeType: 'QUESTION', status: 'INTERRUPTED', elapsedMs: 1 },
        { id: 11, nodeKey: 'question_1', nodeType: 'QUESTION', status: 'SUCCEEDED', elapsedMs: 2 },
      ],
    }

    expect(buildWorkflowRunCallTree(duplicateDetail).map((node) => node.detailKey)).toEqual(['id:10', 'id:11'])
    expect(buildWorkflowRunFlamegraph(duplicateDetail).map((node) => node.detailKey)).toEqual(['id:10', 'id:11'])
  })

  it('formats node token cost latency evidence for run detail', () => {
    expect(formatWorkflowNodeEvidence({
      nodeKey: 'llm',
      nodeType: 'LLM',
      latencyMs: 30,
      inputTokens: 12,
      outputTokens: 8,
      totalTokens: 20,
      costEstimate: '0.001',
      resourceType: 'LLM',
      resourceId: 'model:demo',
      usageEstimated: false,
    })).toEqual('Tokens 20 (12 in / 8 out) · Cost 0.001 · 30ms · LLM model:demo')

    expect(formatWorkflowNodeEvidence({
      nodeKey: 'end',
      nodeType: 'END',
      latencyMs: 3,
      inputTokens: 0,
      outputTokens: 2,
      totalTokens: 2,
      usageEstimated: true,
    })).toEqual('Tokens 2 (estimated) · Cost - · 3ms · END')
  })
})
