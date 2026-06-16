import { describe, expect, it } from 'vitest'

import {
  buildCustomerAssistantStoryQuery,
  customerAssistantStoryIdFromQuery,
  selectCustomerAssistantDemoStoryToOpen,
} from './customerAssistantStoryLinks'

const stories = [
  { storyId: 'refund-baggage', title: '退票 + 行李额' },
  { storyId: 'invoice-flight-change', title: '发票 + 航班动态' },
]

describe('customer assistant story deep links', () => {
  it('reads a valid story id from string or array route query values', () => {
    expect(customerAssistantStoryIdFromQuery({ story: ' refund-baggage ' })).toBe('refund-baggage')
    expect(customerAssistantStoryIdFromQuery({ story: ['invoice-flight-change', 'ignored'] })).toBe(
      'invoice-flight-change',
    )
  })

  it('falls back to the first seeded story when no valid query story exists', () => {
    expect(selectCustomerAssistantDemoStoryToOpen(stories, null, null)).toBe('refund-baggage')
    expect(selectCustomerAssistantDemoStoryToOpen(stories, 'missing-story', null)).toBe('refund-baggage')
    expect(selectCustomerAssistantDemoStoryToOpen([], 'missing-story', null)).toBeNull()
  })

  it('uses a valid query story unless that story is already selected', () => {
    expect(selectCustomerAssistantDemoStoryToOpen(stories, 'invoice-flight-change', null)).toBe(
      'invoice-flight-change',
    )
    expect(selectCustomerAssistantDemoStoryToOpen(stories, 'invoice-flight-change', 'invoice-flight-change')).toBeNull()
  })

  it('preserves unrelated route query values when writing the selected story', () => {
    expect(buildCustomerAssistantStoryQuery({ tab: 'demo', story: 'old' }, 'invoice-flight-change')).toEqual({
      tab: 'demo',
      story: 'invoice-flight-change',
    })
  })
})
