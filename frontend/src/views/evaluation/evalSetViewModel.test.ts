// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import { describeEvalSetCard, normalizeCaseTags } from './evalSetViewModel'

describe('eval set view model', () => {
  it('describes case count and visible tags for manual regression cases', () => {
    expect(describeEvalSetCard({ caseCount: 0 })).toEqual({
      caseCountText: '0 cases',
      tone: 'empty',
    })
    expect(describeEvalSetCard({ caseCount: 3 })).toEqual({
      caseCountText: '3 cases',
      tone: 'ready',
    })
    expect(normalizeCaseTags([' refund ', '', 'policy', 'refund'])).toEqual(['refund', 'policy'])
  })
})
