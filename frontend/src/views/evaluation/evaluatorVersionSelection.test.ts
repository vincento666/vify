import { describe, expect, it } from 'vitest'

import {
  describeSelectedEvaluatorVersions,
  latestEvaluatorVersionSelection,
  selectedEvaluatorVersionIds,
} from './evaluatorVersionSelection'

describe('evaluatorVersionSelection', () => {
  it('defaults selected evaluators to their latest published versions', () => {
    const selection = latestEvaluatorVersionSelection(
      [11, 12],
      {
        11: [
          { id: 101, evaluatorId: 11, version: '0.0.2' },
          { id: 100, evaluatorId: 11, version: '0.0.1' },
        ],
        12: [],
      },
    )

    expect(selection).toEqual({ 11: 101, 12: 0 })
    expect(selectedEvaluatorVersionIds([11, 12], selection)).toEqual([101])
  })

  it('describes selected immutable versions for the confirmation step', () => {
    expect(describeSelectedEvaluatorVersions(
      [11, 12],
      { 11: 101, 12: 0 },
      {
        11: [{ id: 101, evaluatorId: 11, version: '0.0.2' }],
        12: [{ id: 201, evaluatorId: 12, version: '0.0.1' }],
      },
    )).toBe('评估器版本：v0.0.2')
  })
})
