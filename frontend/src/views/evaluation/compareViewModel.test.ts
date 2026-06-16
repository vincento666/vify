// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import {
  candidateRunsForBase,
  findDefaultRunPair,
  formatDelta,
  isComparableRunPair,
  runOptionLabel,
  summarizeCaseChangeCount,
} from './compareViewModel'

describe('compare view model', () => {
  it('formats deltas and case change summaries', () => {
    expect(formatDelta(0.25)).toBe('+25.0%')
    expect(formatDelta(-0.125)).toBe('-12.5%')
    expect(formatDelta(0)).toBe('0.0%')
    expect(summarizeCaseChangeCount('Recovered', 2)).toBe('Recovered 2')
  })

  it('keeps compare choices scoped to two runs from the same experiment', () => {
    const runs = [
      { id: 10, experimentId: 3, aggregateScore: 0.5, failedCases: 2 },
      { id: 9, experimentId: 3, aggregateScore: 0.25, failedCases: 3 },
      { id: 8, experimentId: 2, aggregateScore: 1, failedCases: 0 },
      { id: 7, experimentId: 2, aggregateScore: 0, failedCases: 1 },
    ]

    expect(findDefaultRunPair(runs)).toEqual({ baseRunId: 9, candidateRunId: 10 })
    expect(candidateRunsForBase(runs, 9).map((run) => run.id)).toEqual([10])
    expect(isComparableRunPair(runs, 9, 10)).toBe(true)
    expect(isComparableRunPair(runs, 9, 8)).toBe(false)
    expect(runOptionLabel(runs[0])).toBe('实验 #3 · 运行 #10 · 50.0% · 2 失败')
  })
})
