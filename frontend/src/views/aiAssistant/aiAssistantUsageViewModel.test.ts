import { describe, expect, it } from 'vitest'

import {
  buildUsageHeatmap,
  formatCallCost,
  formatCostState,
  formatOptionalTokenCount,
  formatTokenCount,
  parseUsageUtcDateTime,
  usageDateRange,
} from './aiAssistantUsageViewModel'

describe('AI Assistant usage view model', () => {
  it('formats tokens and never renders unknown cost as zero', () => {
    expect(formatTokenCount(279_000)).toBe('279k')
    expect(formatTokenCount(2_000_000_000)).toBe('2.0B')
    expect(formatCostState({ costUsd: null, costState: 'unknown', unknownCostCount: 2 })).toBe('价格未知')
    expect(formatCostState({ costUsd: '0.0000000100', costState: 'complete', unknownCostCount: 0 })).toBe('<$0.0001')
    expect(formatCallCost('0.0000000100')).toBe('<$0.0001')
    expect(formatOptionalTokenCount(null)).toBe('Token 未知')
    expect(formatCostState({ costUsd: '0.1200000000', costState: 'partial', unknownCostCount: 1 })).toBe(
      '$0.12 + 未知',
    )
  })

  it('builds a complete calendar heatmap with metric-specific intensity', () => {
    const cells = buildUsageHeatmap(
      [
        { date: '2026-07-09', totalTokens: 25, costUsd: '0.01', costState: 'complete' },
        { date: '2026-07-11', totalTokens: 100, costUsd: null, costState: 'unknown' },
      ],
      '2026-07-09',
      '2026-07-11',
      'tokens',
    )
    expect(cells).toHaveLength(3)
    expect(cells.map((cell) => cell.totalTokens)).toEqual([25, 0, 100])
    expect(cells[2].intensity).toBe(5)

    const costCells = buildUsageHeatmap(
      [{ date: '2026-07-11', totalTokens: 100, costUsd: null, costState: 'unknown' }],
      '2026-07-11',
      '2026-07-11',
      'cost',
    )
    expect(costCells[0].unknownCost).toBe(true)
    expect(costCells[0].intensity).toBe(0)
  })

  it('uses a 30-day detail range and 365-day heatmap range', () => {
    expect(usageDateRange(new Date('2026-07-11T12:00:00+08:00'))).toEqual({
      detailFrom: '2026-06-12',
      heatmapFrom: '2025-07-12',
      to: '2026-07-11',
    })
  })

  it('parses backend UTC-naive ledger timestamps as UTC', () => {
    expect(parseUsageUtcDateTime('2026-07-11T03:20:00').toISOString()).toBe('2026-07-11T03:20:00.000Z')
    expect(parseUsageUtcDateTime('2026-07-11T03:20:00+08:00').toISOString()).toBe('2026-07-10T19:20:00.000Z')
  })
})
