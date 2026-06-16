import { describe, expect, it } from 'vitest'

import {
  buildLlmEvaluatorConfig,
  describeLlmDebugResult,
  initialLlmWorkbenchForm,
} from './llmEvaluatorWorkbench'

describe('llmEvaluatorWorkbench', () => {
  it('builds an LLM judge evaluator config from workbench form fields', () => {
    const form = initialLlmWorkbenchForm(42)
    form.prompt = 'Grade refund policy accuracy.'
    form.passingScore = 0.85

    expect(buildLlmEvaluatorConfig(form)).toEqual({
      modelConfigId: 42,
      rubric: 'Grade refund policy accuracy.',
      passingScore: 0.85,
    })
  })

  it('summarizes debug results for the product preview', () => {
    expect(describeLlmDebugResult({ passed: true, score: 0.92, reason: 'good', rawOutput: '{}', modelConfigId: 1, debugPrompt: 'x' }))
      .toBe('通过 · 分数 0.92 · good')
  })
})
