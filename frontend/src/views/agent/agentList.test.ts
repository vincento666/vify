import { describe, expect, it } from 'vitest'
import { formatAgentCreatedAt } from './agentList'

describe('Agent list view model', () => {
  it('formats ISO timestamps as compact minute precision text', () => {
    expect(formatAgentCreatedAt('2026-06-02T14:33:51.331118')).toBe('2026-06-02 14:33')
  })

  it('uses dash for missing timestamps instead of leaking invalid text', () => {
    expect(formatAgentCreatedAt('')).toBe('-')
    expect(formatAgentCreatedAt(null)).toBe('-')
  })
})
