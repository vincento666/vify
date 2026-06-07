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
