// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { composerNavItems } from '../appNavigation'

describe('customer assistant route and navigation contract', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('exposes the operator panel as a main-menu module', () => {
    const entry = composerNavItems.find((item) => item.path === '/customer-assistant')

    expect(entry?.label).toBe('客服助手')
    expect(entry?.icon).toBeTruthy()
  })

  it('registers the customer assistant route with module metadata', async () => {
    const { default: router } = await import('./index')
    const route = router.getRoutes().find((item) => item.path === '/customer-assistant')

    expect(route).toBeTruthy()
    expect(route?.meta.customerAssistant).toBe(true)
  })
})
