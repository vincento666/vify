import { describe, expect, it } from 'vitest'

import {
  buildAgentPreviewDebugTrace,
  summarizeAgentPreviewRunDebug,
} from './agentPreviewDebug'

describe('agent preview debug view model', () => {
  const detail = {
    previewRunId: 31,
    agentId: 12,
    sessionId: 31,
    status: '成功',
    finishReason: 'stop',
    elapsedMs: 1200,
    firstResponseMs: 240,
    latencyMs: 1188,
    inputChars: 8,
    outputChars: 16,
    input: { content: 'hello' },
    output: { content: 'hello back' },
    startedAt: '2026-06-03T01:02:03',
    nodes: [
      { id: 'user', depth: 0, active: true, icon: '↪', label: '用户输入', detail: 'UserInput' },
      { id: 'llm', depth: 1, active: false, icon: '●', label: '调用 LLM', detail: 'Mimo Flash' },
    ],
    axisTicks: [200, 400, 600, 800, 1000],
    flameLanes: [
      { id: 'user', label: '用户输入 UserInput', offsetPct: 0, widthPct: 20 },
      { id: 'llm', label: '调用 LLM Mimo Flash', offsetPct: 20, widthPct: 80 },
    ],
  }

  it('summarizes preview run identity for deep-linked debug detail', () => {
    expect(summarizeAgentPreviewRunDebug(detail)).toEqual({
      runLabel: 'Preview Run #31',
      statusLabel: '成功',
      charsLabel: '输入 8 字 / 输出 16 字',
    })
  })

  it('maps backend preview run debug detail to the existing call-tree/flamegraph panel model', () => {
    expect(buildAgentPreviewDebugTrace(detail)).toMatchObject({
      keyword: 'hello',
      runId: '31',
      status: '成功',
      finishReason: 'stop',
      elapsedMs: 1200,
      firstResponseMs: 240,
      latencyMs: 1188,
      nodes: detail.nodes,
      flameLanes: detail.flameLanes,
    })
  })
})
