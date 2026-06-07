import { describe, expect, it } from 'vitest'

import { buildChatflowStreamPreview, buildChatflowWelcomeState, formatChatflowAssistantText } from './chatflowTrialRun'

describe('chatflow trial run helpers', () => {
  it('normalizes opening message and suggested questions like Agent preview', () => {
    expect(buildChatflowWelcomeState(' 你好，我能帮你处理售后问题。 ', [' 如何退款？ ', '', '查订单状态', '如何退款？'])).toEqual({
      openingMessage: '你好，我能帮你处理售后问题。',
      suggestedQuestions: ['如何退款？', '查订单状态'],
    })
  })

  it('formats assistant output without leaking null JSON payloads', () => {
    expect(formatChatflowAssistantText({ final: '完成' })).toBe('完成')
    expect(formatChatflowAssistantText({ output: '机器人收到' })).toBe('机器人收到')
    expect(formatChatflowAssistantText({ output: null })).toBe('暂无回复内容')
    expect(formatChatflowAssistantText({ interrupt: { type: 'TRANSFER_TO_HUMAN', message: '已转人工' } })).toBe('已转人工')
  })

  it('accumulates Chatflow stream events without duplicating final content', () => {
    const preview = buildChatflowStreamPreview([
      { type: 'message_delta', nodeKey: 'message_1', content: '你' },
      { type: 'llm_delta', nodeKey: 'llm_1', content: '好' },
      { type: 'node_usage', nodeKey: 'llm_1', inputTokens: 8, outputTokens: 2 },
      { type: 'message_done', nodeKey: 'end', content: '你好' },
    ], { final: 'fallback' })

    expect(preview).toEqual({
      content: '你好',
      chunks: ['你', '好'],
      done: true,
      error: '',
      finalContent: '你好',
      streaming: false,
    })
    expect(formatChatflowAssistantText({ final: 'fallback' }, preview)).toBe('你好')
  })

  it('keeps partial stream content visible before done arrives', () => {
    const preview = buildChatflowStreamPreview([
      { type: 'message_delta', nodeKey: 'message_1', content: '正在' },
      { type: 'message_delta', nodeKey: 'message_1', content: '回复' },
    ])

    expect(preview).toMatchObject({
      content: '正在回复',
      chunks: ['正在', '回复'],
      done: false,
      streaming: true,
    })
  })
})
