import { describe, expect, it } from 'vitest'

import type { AiAssistantEvent } from '@/api/aiAssistant'
import { buildAiAssistantTimeline } from './aiAssistantTimeline'

describe('ai assistant execution timeline', () => {
  it('maps durable run events into visible Codex-style execution cards', () => {
    const events: AiAssistantEvent[] = [
      {
        id: 1,
        sessionId: 1,
        runId: 2,
        sequence: 1,
        type: 'run.started',
        level: 'info',
        status: 'COMPLETED',
        visibleTitle: 'Run started',
        visibleSummary: 'The assistant run started.',
        payload: {},
        createdAt: '2026-06-17T10:00:00',
      },
      {
        id: 2,
        sessionId: 1,
        runId: 2,
        sequence: 2,
        type: 'model.stream_chunk',
        level: 'info',
        status: 'COMPLETED',
        visibleTitle: '模型输出',
        visibleSummary: '我先读取文件。',
        payload: { chunk: '我先读取文件。', streaming: true },
        createdAt: '2026-06-17T10:00:01',
      },
      {
        id: 3,
        sessionId: 1,
        runId: 2,
        sequence: 3,
        type: 'tool.call_output',
        level: 'info',
        status: 'COMPLETED',
        visibleTitle: 'Tool output',
        visibleSummary: 'long output',
        payload: { output: { echo: 'hello' } },
        createdAt: '2026-06-17T10:00:02',
      },
      {
        id: 4,
        sessionId: 1,
        runId: 2,
        sequence: 4,
        type: 'approval.required',
        level: 'info',
        status: 'WAITING',
        visibleTitle: 'Approval required',
        visibleSummary: 'update_customer_profile requires approval.',
        payload: { approvalId: 9, riskLevel: 'BUSINESS_WRITE' },
        createdAt: '2026-06-17T10:00:03',
      },
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline.map((item) => item.kind)).toEqual(['phase', 'model-output', 'tool-output', 'approval'])
    expect(timeline[0].tone).toBe('running')
    expect(timeline[1].summary).toBe('我先读取文件。')
    expect(timeline[2].payloadPreview).toContain('hello')
    expect(timeline[3].approvalId).toBe(9)
  })

  it('assembles consecutive model stream chunks into one visible model output message', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'run.started', '运行开始', 'started', {}),
      event(2, 'model.stream_chunk', '流式输出', '我先', { chunk: '我先', streaming: true }),
      event(3, 'model.stream_chunk', '流式输出', '读取', { chunk: '读取', streaming: true }),
      event(4, 'model.stream_chunk', '流式输出', '文件。', { chunk: '文件。', streaming: true }),
      event(5, 'tool.call_output', '工具输出', 'AGENTS.md', { output: { path: 'AGENTS.md' } }),
      event(6, 'model.stream_chunk', '模型输出', '最终', {
        chunk: '最终',
        phase: 'final_answer',
        streaming: true,
      }),
      event(7, 'model.stream_chunk', '模型输出', '回答。', {
        chunk: '回答。',
        phase: 'final_answer',
        streaming: true,
      }),
      event(8, 'approval.required', '需要审批', '写入需要审批。', { approvalId: 9 }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline.map((item) => item.kind)).toEqual([
      'phase',
      'model-output',
      'tool-output',
      'model-output',
      'approval',
    ])
    expect(timeline[1].summary).toBe('我先读取文件。')
    expect(timeline[1].payloadPreview).toContain('"chunkCount":3')
    expect(timeline[3].summary).toBe('最终回答。')
    expect(timeline[3].sequence).toBe(6)
    expect(timeline[4].approvalId).toBe(9)
  })
})

function event(
  sequence: number,
  type: string,
  visibleTitle: string,
  visibleSummary: string,
  payload: Record<string, unknown>,
): AiAssistantEvent {
  return {
    id: sequence,
    sessionId: 1,
    runId: 2,
    sequence,
    type,
    level: 'info',
    status: type === 'approval.required' ? 'WAITING' : 'COMPLETED',
    visibleTitle,
    visibleSummary,
    payload,
    createdAt: '2026-06-17T10:00:00',
  }
}
