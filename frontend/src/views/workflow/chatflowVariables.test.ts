import { describe, expect, it } from 'vitest'

import { buildChatflowVariableScopes, insertChatflowVariableReference } from './chatflowVariables'

describe('chatflow variables', () => {
  it('groups default variables by Chatflow scope', () => {
    const scopes = buildChatflowVariableScopes()

    expect(scopes.map((scope) => scope.title)).toEqual([
      'System',
      'Global',
      'Conversation',
      'User',
      'Channel',
      'External Input',
    ])
    expect(scopes[0].items.map((item) => item.reference)).toEqual(
      expect.arrayContaining(['{{sys.query}}', '{{sys.conversation_id}}', '{{sys.user_id}}', '{{sys.channel}}']),
    )
  })

  it('inserts selected variables into a field without dropping existing text', () => {
    expect(insertChatflowVariableReference('你好', '{{sys.query}}')).toBe('你好 {{sys.query}}')
    expect(insertChatflowVariableReference('', '{{user.name}}')).toBe('{{user.name}}')
  })
})
