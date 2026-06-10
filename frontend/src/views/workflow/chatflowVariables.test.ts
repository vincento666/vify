import { describe, expect, it } from 'vitest'

import { buildChatflowVariableScopes, insertChatflowVariableReference } from './chatflowVariables'

describe('chatflow variables', () => {
  it('shows only configured runtime context variables by default', () => {
    const scopes = buildChatflowVariableScopes()

    expect(scopes.map((scope) => scope.title)).toEqual(['会话变量', '用户变量'])
    expect(scopes[0].description).toContain('会话')
    expect(scopes[0].items[0]).toMatchObject({
      key: 'SYS_QUERY',
      label: '本轮输入',
      reference: '{{sys.query}}',
      readonly: true,
    })
    expect(scopes[0].items.map((item) => item.reference)).toEqual(
      expect.arrayContaining([
        '{{sys.query}}',
        '{{sys.conversation_id}}',
        '{{sys.user_id}}',
        '{{sys.channel}}',
        '{{sys.channel_id}}',
      ]),
    )
    expect(scopes.flatMap((scope) => scope.items.map((item) => item.reference))).not.toEqual(
      expect.arrayContaining(['{{global.brand}}', '{{user.name}}', '{{conversation.topic}}', '{{input.payload}}']),
    )
  })

  it('includes configured conversation and user variables after runtime defaults', () => {
    const scopes = buildChatflowVariableScopes({
      conversationVariables: [{ name: 'customer_level', label: '客户等级', type: 'string' }],
      userVariables: [{ name: 'language', label: '语言偏好', type: 'string' }],
    })

    expect(scopes[0].items).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: 'customer_level',
          label: '客户等级',
          reference: '{{conversation.customer_level}}',
          readonly: false,
        }),
      ]),
    )
    expect(scopes[1].items).toEqual([
      expect.objectContaining({
        key: 'language',
        label: '语言偏好',
        reference: '{{user.language}}',
        readonly: false,
      }),
    ])
  })

  it('inserts selected variables into a field without dropping existing text', () => {
    expect(insertChatflowVariableReference('你好', '{{sys.query}}')).toBe('你好 {{sys.query}}')
    expect(insertChatflowVariableReference('', '{{user.name}}')).toBe('{{user.name}}')
  })
})
