// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import {
  formatRunSummary,
  formatTargetLabel,
  runSummaryMetricItems,
  runStatusTone,
  targetTypeOptions,
} from './experimentRunViewModel'

describe('experiment run view model', () => {
  it('summarizes run score, pass rate, and status tone', () => {
    expect(formatRunSummary({ aggregateScore: 0.875, passRate: 0.5, failedCases: 2 })).toEqual({
      scoreText: '87.5%',
      passRateText: '50.0%',
      failedText: '2 failed',
    })
    expect(runStatusTone('COMPLETED')).toBe('success')
    expect(runStatusTone('FAILED')).toBe('danger')
  })

  it('exposes selectable evaluation target types', () => {
    expect(targetTypeOptions.map((item) => item.value)).toEqual(['AGENT', 'WORKFLOW', 'CHATFLOW'])
    expect(formatTargetLabel({ targetType: 'WORKFLOW', targetId: 12 })).toBe('Workflow #12')
    expect(formatTargetLabel({ targetType: 'CHATFLOW', targetId: 13 })).toBe('Chatflow #13')
  })

  it('exposes compact report metrics for run record headers', () => {
    expect(runSummaryMetricItems({ aggregateScore: 0.875, passRate: 0.5, failedCases: 2 })).toEqual([
      { label: 'Score', value: '87.5%' },
      { label: 'Pass', value: '50.0%' },
      { label: 'Failed', value: '2' },
    ])
  })
})
