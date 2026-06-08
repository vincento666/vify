import { describe, expect, it } from 'vitest'

import { buildChatflowRunInput } from './chatflowRunProfile'

describe('buildChatflowRunInput', () => {
  it('maps a conversation test profile to sys variables and compatibility fields', () => {
    const input = buildChatflowRunInput({
      message: '我要查订单',
      conversationId: 'conv-1',
      userId: 'user-1',
      channel: 'web',
      channelId: 'web-preview',
      round: 3,
    })

    expect(input).toMatchObject({
      userMessage: '我要查订单',
      USER_INPUT: '我要查订单',
      'sys.query': '我要查订单',
      'sys.conversation_id': 'conv-1',
      'sys.user_id': 'user-1',
      'sys.channel': 'web',
      'sys.channel_id': 'web-preview',
      'sys.round': 3,
      'global.brand': 'Hify',
      'global.locale': 'zh-CN',
    })
    expect(input.global).toEqual({ brand: 'Hify', locale: 'zh-CN' })
    expect(input.sys).toMatchObject({ channel_id: 'web-preview' })
    expect(input['sys.message_id']).toMatch(/^msg-/)
  })

  it('passes chatflow history retention rounds as runtime metadata', () => {
    const input = buildChatflowRunInput({
      message: '继续',
      conversationId: 'conv-1',
      userId: 'user-1',
      channel: 'web',
      round: 2,
      historyRetentionRounds: 0,
    })

    expect(input).toMatchObject({
      'sys.history_retention_rounds': 0,
      historyRetentionRounds: 0,
    })
    expect(input.sys).toMatchObject({ history_retention_rounds: 0 })
  })
})
