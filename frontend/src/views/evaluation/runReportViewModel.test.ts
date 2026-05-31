// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import { failureInvestigationTitle, filterCaseResults, rerunActionLabel } from './runReportViewModel'

describe('run report view model', () => {
  it('filters failed cases and names the investigation state', () => {
    const cases = [
      { id: 1, status: 'PASSED' },
      { id: 2, status: 'FAILED' },
    ]

    expect(filterCaseResults(cases, 'FAILED')).toEqual([{ id: 2, status: 'FAILED' }])
    expect(failureInvestigationTitle(3)).toBe('3 failed cases need investigation')
    expect(rerunActionLabel({ status: 'FAILED' })).toBe('重跑失败用例')
    expect(rerunActionLabel({ status: 'PASSED' })).toBe('重跑用例')
  })
})
