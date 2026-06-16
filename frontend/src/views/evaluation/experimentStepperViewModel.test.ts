import { describe, expect, it } from 'vitest'

import {
  EXPERIMENT_CREATE_STEPS,
  advanceExperimentStep,
  describeExperimentStep,
  retreatExperimentStep,
} from './experimentStepperViewModel'

describe('experimentStepperViewModel', () => {
  it('defines the Coze-like experiment creation steps in order', () => {
    expect(EXPERIMENT_CREATE_STEPS.map((step) => step.key)).toEqual([
      'basic',
      'eval-set',
      'target',
      'evaluator',
      'confirm',
    ])
    expect(EXPERIMENT_CREATE_STEPS.map((step) => step.title)).toEqual([
      '基础信息',
      '评测集',
      '评测对象',
      '评估器',
      '确认',
    ])
  })

  it('moves forward and backward without leaving the step bounds', () => {
    expect(advanceExperimentStep('basic')).toBe('eval-set')
    expect(advanceExperimentStep('confirm')).toBe('confirm')
    expect(retreatExperimentStep('confirm')).toBe('evaluator')
    expect(retreatExperimentStep('basic')).toBe('basic')
  })

  it('describes current step position for the UI', () => {
    expect(describeExperimentStep('target')).toEqual({
      index: 2,
      positionText: '3 / 5',
      isFirst: false,
      isLast: false,
    })
  })
})
