import { describe, expect, it } from 'vitest'

import { buildChatflowVariableScopes, insertChatflowVariableReference } from './chatflowVariables'

describe('chatflow variables', () => {
  it('shows only configured runtime context variables by default', () => {
    const scopes = buildChatflowVariableScopes()

    expect(scopes.map((scope) => scope.title)).toEqual(['运行上下文'])
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

  it('inserts selected variables into a field without dropping existing text', () => {
    expect(insertChatflowVariableReference('你好', '{{sys.query}}')).toBe('你好 {{sys.query}}')
    expect(insertChatflowVariableReference('', '{{user.name}}')).toBe('{{user.name}}')
  })
})
