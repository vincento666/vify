export type ExperimentCreateStepKey = 'basic' | 'eval-set' | 'target' | 'evaluator' | 'confirm'

export interface ExperimentCreateStep {
  key: ExperimentCreateStepKey
  title: string
  description: string
}

export const EXPERIMENT_CREATE_STEPS: ExperimentCreateStep[] = [
  { key: 'basic', title: '基础信息', description: '命名实验并设置运行参数。' },
  { key: 'eval-set', title: '评测集', description: '选择本次实验使用的数据版本。' },
  { key: 'target', title: '评测对象', description: '选择 Agent、Workflow 或 Chatflow。' },
  { key: 'evaluator', title: '评估器', description: '选择一个或多个评分规则。' },
  { key: 'confirm', title: '确认', description: '运行前复核配置。' },
]

export interface ExperimentStepDescription {
  index: number
  positionText: string
  isFirst: boolean
  isLast: boolean
}

function stepIndex(step: ExperimentCreateStepKey): number {
  return Math.max(0, EXPERIMENT_CREATE_STEPS.findIndex((item) => item.key === step))
}

export function advanceExperimentStep(step: ExperimentCreateStepKey): ExperimentCreateStepKey {
  const index = stepIndex(step)
  return EXPERIMENT_CREATE_STEPS[Math.min(index + 1, EXPERIMENT_CREATE_STEPS.length - 1)].key
}

export function retreatExperimentStep(step: ExperimentCreateStepKey): ExperimentCreateStepKey {
  const index = stepIndex(step)
  return EXPERIMENT_CREATE_STEPS[Math.max(index - 1, 0)].key
}

export function describeExperimentStep(step: ExperimentCreateStepKey): ExperimentStepDescription {
  const index = stepIndex(step)
  return {
    index,
    positionText: `${index + 1} / ${EXPERIMENT_CREATE_STEPS.length}`,
    isFirst: index === 0,
    isLast: index === EXPERIMENT_CREATE_STEPS.length - 1,
  }
}
