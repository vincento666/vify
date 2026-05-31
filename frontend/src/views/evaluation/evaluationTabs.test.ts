// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import { EVALUATION_TABS, getActiveEvaluationTab } from './evaluationTabs'

describe('evaluation tabs', () => {
  it('orders Evaluation workbench tabs around the experiment task flow', () => {
    expect(EVALUATION_TABS.map((tab) => tab.key)).toEqual([
      'experiments',
      'eval-sets',
      'evaluators',
      'runs',
      'compare',
    ])
    expect(EVALUATION_TABS[0].label).toBe('Experiments')
    expect(EVALUATION_TABS[4].disabled).toBe(false)
  })

  it('maps query tab keys to a safe active tab', () => {
    expect(getActiveEvaluationTab('evaluators')).toBe('evaluators')
    expect(getActiveEvaluationTab('missing')).toBe('experiments')
    expect(getActiveEvaluationTab(undefined)).toBe('experiments')
  })
})
