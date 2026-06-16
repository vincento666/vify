import type { LlmEvaluatorDebugResult } from '@/api/evaluation'

export interface LlmWorkbenchForm {
  name: string
  modelConfigId: number
  prompt: string
  expectedOutput: string
  actualOutput: string
  passingScore: number
}

export function initialLlmWorkbenchForm(modelConfigId = 0): LlmWorkbenchForm {
  return {
    name: '',
    modelConfigId,
    prompt: '实际输出满足期望答案时通过。',
    expectedOutput: '',
    actualOutput: '',
    passingScore: 0.7,
  }
}

export function buildLlmEvaluatorConfig(form: LlmWorkbenchForm) {
  return {
    modelConfigId: form.modelConfigId,
    rubric: form.prompt.trim(),
    passingScore: Number(form.passingScore) || 0.7,
  }
}

export function describeLlmDebugResult(result: LlmEvaluatorDebugResult): string {
  return `${result.passed ? '通过' : '失败'} · 分数 ${result.score} · ${result.reason}`
}
