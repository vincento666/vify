// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'

import { canAccessComposerNavItem, composerNavItems } from '@/appNavigation'

describe('runtime ops route and navigation contract', () => {
  it('exposes runtime ops as a guarded main-menu module', async () => {
    const { default: router } = await import('./index')

    const route = router.getRoutes().find((item) => item.path === '/runtime-ops')
    const navItem = composerNavItems.find((item) => item.path === '/runtime-ops')

    expect(route).toBeTruthy()
    expect(route?.name).toBe('HifyRuntimeOps')
    expect(route?.meta.runtimeOps).toBe(true)
    expect(route?.meta.requiredPermission).toBe('runtime_ops:read')
    expect(navItem?.name).toBe('HifyRuntimeOps')
    expect(navItem?.label).toBe('运行观测')
    expect(navItem?.requiredPermission).toBe('runtime_ops:read')
    expect(navItem?.icon).toBeTruthy()
  }, 15000)

  it('keeps local development open but gates host-scoped runtime ops access', () => {
    const navItem = composerNavItems.find((item) => item.path === '/runtime-ops')

    expect(navItem).toBeTruthy()
    expect(canAccessComposerNavItem(navItem!, {})).toBe(true)
    expect(canAccessComposerNavItem(navItem!, { permissions: ['workflow:run'] })).toBe(false)
    expect(canAccessComposerNavItem(navItem!, { permissions: ['runtime_ops:read'] })).toBe(true)
  })
})
