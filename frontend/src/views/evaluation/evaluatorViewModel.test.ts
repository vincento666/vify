// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import { describeEvaluatorType, keywordConfigFromText } from './evaluatorViewModel'

describe('evaluator view model', () => {
  it('normalizes evaluator labels and keyword config', () => {
    expect(describeEvaluatorType('EXACT_MATCH')).toBe('精确匹配')
    expect(describeEvaluatorType('CONTAINS_KEYWORDS')).toBe('包含关键词')
    expect(describeEvaluatorType('LLM_JUDGE')).toBe('LLM 裁判')
    expect(keywordConfigFromText(' refund, policy, refund ')).toEqual({
      keywords: ['refund', 'policy'],
      matchMode: 'all',
      ignoreCase: true,
    })
  })
})
