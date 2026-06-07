export interface VariableBraceTriggerResult {
  value: string
  caret: number | null
  opened: boolean
}

export function completeVariableBraceTrigger(value: string, previousValue = ''): VariableBraceTriggerResult {
  const isTypingForward = value.length > previousValue.length

  if (isTypingForward && value.endsWith('{') && !value.endsWith('{{')) {
    const prefix = value.slice(0, -1)
    return {
      value: `${prefix}{{}}`,
      caret: prefix.length + 2,
      opened: true,
    }
  }

  return {
    value,
    caret: null,
    opened: isTypingForward && value.endsWith('{{'),
  }
}

export function insertInlineVariableReference(currentValue: string, reference: string) {
  const doubleBracePairIndex = currentValue.lastIndexOf('{{}}')
  if (doubleBracePairIndex >= 0) {
    return `${currentValue.slice(0, doubleBracePairIndex)}${reference}${currentValue.slice(doubleBracePairIndex + 4)}`
  }

  const bracePairIndex = currentValue.lastIndexOf('{}')
  if (bracePairIndex >= 0) {
    return `${currentValue.slice(0, bracePairIndex)}${reference}${currentValue.slice(bracePairIndex + 2)}`
  }

  const triggerIndex = currentValue.lastIndexOf('{{')
  if (triggerIndex >= 0) {
    return `${currentValue.slice(0, triggerIndex)}${reference}${currentValue.slice(triggerIndex + 2)}`
  }

  return currentValue ? `${currentValue} ${reference}` : reference
}
