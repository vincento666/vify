export interface RunSummaryInput {
  aggregateScore: number
  passRate: number
  failedCases: number
}

export type EvaluationTargetType = 'AGENT' | 'WORKFLOW' | 'CHATFLOW'

export interface TargetLabelInput {
  targetType: EvaluationTargetType
  targetId: number
}

export const targetTypeOptions: Array<{ label: string; value: EvaluationTargetType }> = [
  { label: 'Agent', value: 'AGENT' },
  { label: 'Workflow', value: 'WORKFLOW' },
  { label: 'Chatflow', value: 'CHATFLOW' },
]

export function formatRunSummary(run: RunSummaryInput) {
  return {
    scoreText: `${(run.aggregateScore * 100).toFixed(1)}%`,
    passRateText: `${(run.passRate * 100).toFixed(1)}%`,
    failedText: `${run.failedCases} failed`,
  }
}

export function runStatusTone(status: string): 'success' | 'warning' | 'danger' {
  if (status === 'COMPLETED') return 'success'
  if (status === 'FAILED') return 'danger'
  return 'warning'
}

export function formatTargetLabel(input: TargetLabelInput) {
  const option = targetTypeOptions.find((item) => item.value === input.targetType)
  return `${option?.label || input.targetType} #${input.targetId}`
}
