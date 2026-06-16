// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import {
  failureInvestigationTitle,
  filterCaseResults,
  rerunActionLabel,
  targetEvidenceActionLabel,
  targetEvidenceHref,
} from './runReportViewModel'

describe('run report view model', () => {
  it('filters failed cases and names the investigation state', () => {
    const cases = [
      { id: 1, status: 'PASSED' },
      { id: 2, status: 'FAILED' },
    ]

    expect(filterCaseResults(cases, 'FAILED')).toEqual([{ id: 2, status: 'FAILED' }])
    expect(failureInvestigationTitle(3)).toBe('3 个失败用例需要排查')
    expect(rerunActionLabel({ status: 'FAILED' })).toBe('重跑失败用例')
    expect(rerunActionLabel({ status: 'PASSED' })).toBe('重跑用例')
  })

  it('builds target debug evidence actions for failed-case drilldown', () => {
    const workflowCase = {
      targetType: 'WORKFLOW',
      targetDebugUrl: '/workflows/12/canvas?runId=34&debug=1',
    }
    const chatflowCase = {
      targetType: 'CHATFLOW',
      targetDebugUrl: '/chatflows/56/canvas?runId=78&debug=1',
    }

    expect(targetEvidenceActionLabel(workflowCase)).toBe('查看 Workflow 调试')
    expect(targetEvidenceHref(workflowCase)).toBe('/workflows/12/canvas?runId=34&debug=1')
    expect(targetEvidenceActionLabel(chatflowCase)).toBe('查看 Chatflow 调试')
    expect(targetEvidenceActionLabel({ targetType: 'AGENT', targetDebugUrl: '' })).toBe('')
  })
})
