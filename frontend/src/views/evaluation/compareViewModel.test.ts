// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import { formatDelta, summarizeCaseChangeCount } from './compareViewModel'

describe('compare view model', () => {
  it('formats deltas and case change summaries', () => {
    expect(formatDelta(0.25)).toBe('+25.0%')
    expect(formatDelta(-0.125)).toBe('-12.5%')
    expect(formatDelta(0)).toBe('0.0%')
    expect(summarizeCaseChangeCount('Recovered', 2)).toBe('Recovered 2')
  })
})
