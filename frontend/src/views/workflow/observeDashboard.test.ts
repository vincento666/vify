import { describe, expect, it } from 'vitest'

import { buildObserveMetricTiles, normalizeObserveRunIdQuery } from './observeDashboard'

describe('observe dashboard view model', () => {
  it('formats run, handoff, and channel metrics into scan-friendly tiles', () => {
    expect(buildObserveMetricTiles({
      runCount: 12,
      handoffCount: 3,
      handoffRate: 0.25,
      channelDistribution: { web: 10, api: 2 },
      channelDeliveryFailures: 2,
    })).toEqual([
      { label: 'Runs', value: '12' },
      { label: 'Handoffs', value: '3' },
      { label: 'Handoff Rate', value: '25.0%' },
      { label: 'Top Channel', value: 'web 10' },
      { label: 'Channel Failures', value: '2' },
    ])
  })

  it('normalizes observe run query into a concrete run id', () => {
    expect(normalizeObserveRunIdQuery('841')).toBe(841)
    expect(normalizeObserveRunIdQuery(['42'])).toBe(42)
    expect(normalizeObserveRunIdQuery('0')).toBe(0)
    expect(normalizeObserveRunIdQuery('abc')).toBe(0)
  })
})
