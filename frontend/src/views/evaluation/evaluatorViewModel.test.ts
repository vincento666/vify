// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import { describeEvaluatorType, keywordConfigFromText } from './evaluatorViewModel'

describe('evaluator view model', () => {
  it('normalizes evaluator labels and keyword config', () => {
    expect(describeEvaluatorType('EXACT_MATCH')).toBe('Exact Match')
    expect(describeEvaluatorType('CONTAINS_KEYWORDS')).toBe('Contains Keywords')
    expect(describeEvaluatorType('LLM_JUDGE')).toBe('LLM Judge')
    expect(keywordConfigFromText(' refund, policy, refund ')).toEqual({
      keywords: ['refund', 'policy'],
      matchMode: 'all',
      ignoreCase: true,
    })
  })
})
