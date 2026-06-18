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

    expect(timeline.map((item) => item.kind)).toEqual(['phase', 'model-output', 'tool', 'approval'])
    expect(timeline[0].tone).toBe('running')
    expect(timeline[1].summary).toBe('我先读取文件。')
    expect(timeline[2].details.map((detail) => detail.label)).toEqual(['调用详情', '输入', '输出'])
    expect(timeline[2].details.find((detail) => detail.label === '输出')?.value).toContain('hello')
    expect(timeline[3].approvalId).toBe(9)
  })

  it('assembles consecutive model stream chunks into one visible model output message', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'run.started', '运行开始', 'started', {}),
      event(2, 'model.stream_chunk', '流式输出', '我先', { chunk: '我先', streaming: true }),
      event(3, 'model.stream_chunk', '流式输出', '读取', { chunk: '读取', streaming: true }),
      event(4, 'model.stream_chunk', '流式输出', '文件。', { chunk: '文件。', streaming: true }),
      event(5, 'tool.call_output', '工具输出', 'AGENTS.md', { toolName: 'read_workspace_file', output: { path: 'AGENTS.md' } }),
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
      'tool',
      'model-output',
      'approval',
    ])
    expect(timeline[1].summary).toBe('我先读取文件。')
    expect(timeline[1].phase).toBeUndefined()
    expect(timeline[1].payloadPreview).toContain('"chunkCount":3')
    expect(timeline[3].summary).toBe('最终回答。')
    expect(timeline[3].sequence).toBe(6)
    expect(timeline[3].phase).toBe('final_answer')
    expect(timeline[4].approvalId).toBe(9)
  })

  it('carries stream phase and source metadata for final answer placement', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'model.stream_chunk', '模型输出', '最终', {
        chunk: '最终',
        phase: 'final_answer',
        source: 'harness_final_answer',
      }),
      event(2, 'model.stream_chunk', '模型输出', '回答', {
        chunk: '回答',
        phase: 'final_answer',
        source: 'harness_final_answer',
      }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline).toHaveLength(1)
    expect(timeline[0]).toMatchObject({
      kind: 'model-output',
      summary: '最终回答',
      phase: 'final_answer',
      source: 'harness_final_answer',
    })
  })

  it('deduplicates thought summaries that repeat the visible model output', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'model.stream_chunk', '模型输出', '我会先读取文件。', { chunk: '我会先读取文件。' }),
      event(2, 'model.thought_summary', '思考摘要', '我会先读取文件。', {
        summary: '我会先读取文件。',
      }),
      event(3, 'model.thought_summary', '思考摘要', '需要比对配置和测试结果。', {
        summary: '需要比对配置和测试结果。',
      }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline.map((item) => item.kind)).toEqual(['model-output', 'model-thought'])
    expect(timeline[1].title).toBe('思考')
    expect(timeline[1].summary).toBe('需要比对配置和测试结果。')
  })

  it('deduplicates thought summaries that arrive immediately before the same stream output', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'model.thought_summary', '思考摘要', '已根据请求规划工具调用。', {
        summary: '已根据请求规划工具调用。',
      }),
      event(2, 'model.stream_chunk', '模型输出', '已根据请求', { chunk: '已根据请求' }),
      event(3, 'model.stream_chunk', '模型输出', '规划工具调用。', { chunk: '规划工具调用。' }),
      event(4, 'model.tool_call_decision', '工具调用决策', '模型已选择工具调用。', {
        toolNames: ['read_workspace_file'],
      }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline.map((item) => item.kind)).toEqual(['model-output', 'model'])
    expect(timeline[0].summary).toBe('已根据请求规划工具调用。')
  })

  it('keeps a tool invocation as one foldable call with input output and execution detail', () => {
    const events: AiAssistantEvent[] = [
      event(1, 'tool.call_started', '工具开始', '读取工作区文件 已开始执行。', {
        toolName: 'read_workspace_file',
        input: { path: 'AGENTS.md' },
      }),
      event(2, 'tool.call_output', '工具输出', 'project instructions', {
        toolName: 'read_workspace_file',
        output: { text: 'project instructions' },
      }),
      event(3, 'tool.call_completed', '工具完成', '读取工作区文件 已完成。', {
        toolName: 'read_workspace_file',
        status: 'OK',
      }),
    ]

    const timeline = buildAiAssistantTimeline(events)

    expect(timeline).toHaveLength(1)
    expect(timeline[0].kind).toBe('tool')
    expect(timeline[0].title).toBe('读取工作区文件')
    expect(timeline[0].tone).toBe('success')
    expect(timeline[0].details.map((detail) => detail.label)).toEqual(['调用详情', '输入', '输出'])
    expect(timeline[0].details[1].value).toContain('AGENTS.md')
    expect(timeline[0].details[2].value).toContain('project instructions')
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
