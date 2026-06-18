// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import { composerNavItems } from '@/appNavigation'

describe('AI Assistant route', () => {
  it('registers a product-shell route and navigation item', async () => {
    const { default: router } = await import('./index')

    expect(router.getRoutes().some((route) => route.name === 'HifyAiAssistant')).toBe(true)
    expect(
      composerNavItems.some((item) => item.name === 'HifyAiAssistant' && item.path === '/ai-assistant' && item.label === 'AI 助手'),
    ).toBe(true)
  })
})
