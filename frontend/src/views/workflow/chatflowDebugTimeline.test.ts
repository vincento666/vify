import { describe, expect, it } from 'vitest'

import {
  buildChatflowResumeFields,
  flattenChatflowVariables,
  formatChatflowTimeline,
} from './chatflowDebugTimeline'

describe('chatflow debug timeline view model', () => {
  it('orders events and exposes checkpoint labels', () => {
    const events = formatChatflowTimeline([
      { id: 3, sequence: 3, type: 'resume', nodeKey: 'question_1', checkpointId: 9 },
      { id: 1, sequence: 1, type: 'message', nodeKey: 'question_1', payload: { content: '继续吗？' } },
      { id: 2, sequence: 2, type: 'interrupt', nodeKey: 'question_1', checkpointId: 9 },
    ])

    expect(events.map((event) => event.type)).toEqual(['message', 'interrupt', 'resume'])
    expect(events[1].label).toBe('等待输入')
    expect(events[1].meta).toContain('Checkpoint #9')
  })

  it('labels transfer-to-human handoff events with ticket context', () => {
    const events = formatChatflowTimeline([
      {
        id: 7,
        sequence: 7,
        type: 'handoff_requested',
        nodeKey: 'transfer_to_human_1',
        payload: { content: '', handoffId: 12, queue: 'vip-support', status: 'queued' },
      },
    ])

    expect(events[0]).toMatchObject({
      label: '转人工',
      nodeKey: 'transfer_to_human_1',
      content: '工单 #12 · vip-support · queued',
    })
  })

  it('formats runtime v2 node ids and workflow event names for chatflow timelines', () => {
    const events = formatChatflowTimeline([
      {
        id: 8,
        sequence: 8,
        type: 'workflow_node_waiting',
        nodeId: 'question_1',
        payload: { question: '主题？' },
        checkpointId: 4,
      },
      {
        id: 9,
        sequence: 9,
        type: 'handoff_requested',
        nodeId: 'transfer_to_human_1',
        payload: {
          handoffId: 'runtime-v2-handoff-91-transfer_to_human_1',
          queue: 'vip-support',
          status: 'waiting',
        },
      },
    ])

    expect(events[0]).toMatchObject({
      label: '等待输入',
      nodeKey: 'question_1',
      content: '主题？',
    })
    expect(events[0].meta).toContain('Checkpoint #4')
    expect(events[1]).toMatchObject({
      label: '转人工',
      nodeKey: 'transfer_to_human_1',
      content: '工单 #runtime-v2-handoff-91-transfer_to_human_1 · vip-support · waiting',
    })
  })

  it('formats runtime v2 failure evidence while redacting sensitive headers and resume data', () => {
    const events = formatChatflowTimeline([
      {
        id: 10,
        sequence: 10,
        type: 'workflow_node_failed',
        nodeId: 'api_call_1',
        payload: {
          error: 'HTTP 502 upstream timeout',
          evidence: {
            resourceType: 'API_TOOL',
            statusCode: 502,
            attempt: 3,
            maxAttempts: 3,
            durationMs: 1200,
            request: {
              method: 'POST',
              url: 'https://api.example.com/weather',
              headers: {
                Authorization: 'Bearer secret-token',
                'X-Trace-Id': 'trace-1',
              },
            },
          },
        },
      },
      {
        id: 11,
        sequence: 11,
        type: 'resume',
        nodeId: 'human_input_1',
        checkpointId: 7,
        payload: {
          resumeData: {
            approved: true,
            token: 'secret-token',
          },
        },
      },
    ])

    expect(events[0]).toMatchObject({
      label: '节点失败',
      nodeKey: 'api_call_1',
    })
    expect(events[0].content).toContain('HTTP 502 upstream timeout')
    expect(events[0].content).toContain('status 502')
    expect(events[0].content).toContain('attempt 3/3')
    expect(events[0].content).toContain('Authorization=[REDACTED]')
    expect(events[0].content).toContain('X-Trace-Id=trace-1')
    expect(events[0].content).not.toContain('secret-token')
    expect(events[1].content).toContain('"approved":true')
    expect(events[1].content).toContain('"token":"[REDACTED]"')
    expect(events[1].content).not.toContain('secret-token')
  })

  it('flattens scoped variables for the debug dock', () => {
    const rows = flattenChatflowVariables({
      conversation: { topic: 'refund' },
      user: { tier: 'vip' },
      sys: { query: 'hello' },
    })

    expect(rows).toEqual([
      { scope: 'conversation', name: 'topic', value: 'refund' },
      { scope: 'sys', name: 'query', value: 'hello' },
      { scope: 'user', name: 'tier', value: 'vip' },
    ])
  })

  it('derives resume fields from waiting event schema', () => {
    expect(buildChatflowResumeFields({ type: 'QUESTION', answerType: 'text' })).toEqual([
      { key: 'answer', label: '回复内容', placeholder: '输入回复内容' },
    ])
    expect(buildChatflowResumeFields({ type: 'HUMAN_INPUT', approvalMode: 'approval' })).toEqual([
      { key: 'approved', label: '审批结果', placeholder: 'true / false' },
      { key: 'payload', label: '补充数据', placeholder: 'JSON 或文本' },
    ])
    expect(buildChatflowResumeFields({ type: 'INFORMATION_COLLECTION', missing: ['phone'] })).toEqual([
      { key: 'answer', label: '补充信息', placeholder: '补充 phone' },
    ])
  })
})
