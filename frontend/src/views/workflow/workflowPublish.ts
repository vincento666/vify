export interface WorkflowPublishGateInput {
  validationErrors: string[]
  lastTestRunStatus: string
  dirtySinceTestRun: boolean
}

export interface WorkflowPublishGate {
  allowed: boolean
  reasons: string[]
}

export function evaluateWorkflowPublishGate(input: WorkflowPublishGateInput): WorkflowPublishGate {
  const reasons: string[] = []

  if (input.validationErrors.length > 0) {
    reasons.push('画布校验未通过')
  }

  if (input.lastTestRunStatus !== 'SUCCEEDED') {
    reasons.push('需要先完成一次成功试运行')
  }

  if (input.lastTestRunStatus === 'SUCCEEDED' && input.dirtySinceTestRun) {
    reasons.push('画布已变更，需要重新试运行')
  }

  return {
    allowed: reasons.length === 0,
    reasons,
  }
}
