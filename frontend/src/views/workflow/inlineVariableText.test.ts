import { describe, expect, it } from 'vitest'

import { completeVariableBraceTrigger, insertInlineVariableReference, localizeInlineVariableReference } from './inlineVariableText'

describe('inline variable text editing', () => {
  it('auto-completes a single left brace to a double-brace placeholder with centered caret', () => {
    expect(completeVariableBraceTrigger('hello {')).toEqual({
      value: 'hello {{}}',
      caret: 8,
      opened: true,
    })
  })

  it('does not reopen variable mode for ordinary literal edits', () => {
    expect(completeVariableBraceTrigger('hello world')).toEqual({
      value: 'hello world',
      caret: null,
      opened: false,
    })
  })

  it('does not auto-complete a remaining single brace while deleting a placeholder', () => {
    expect(completeVariableBraceTrigger('{', '{{}}')).toEqual({
      value: '{',
      caret: null,
      opened: false,
    })
  })

  it('replaces the latest empty double-brace placeholder with the selected reference', () => {
    expect(insertInlineVariableReference('hello {{}}', '{{sys.query}}')).toBe('hello {{sys.query}}')
  })

  it('localizes current-node inline references when a field accepts only local inputs', () => {
    expect(localizeInlineVariableReference('{{llm_1.input_1}}', 'llm_1', true)).toBe('{{input_1}}')
    expect(localizeInlineVariableReference('{{start.USER_INPUT}}', 'llm_1', true)).toBe('{{start.USER_INPUT}}')
    expect(localizeInlineVariableReference('{{llm_1.input_1}}', 'llm_1', false)).toBe('{{llm_1.input_1}}')
  })
})
