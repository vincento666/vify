// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('unified routing chat lab route', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('exposes a top-level composer menu entry and dedicated route', async () => {
    const [{ default: router }, { composerNavItems }] = await Promise.all([
      import('./index'),
      import('../appNavigation'),
    ])

    const route = router.getRoutes().find((item) => item.path === '/runtime-lab/chat')
    const navItem = composerNavItems.find((item) => item.path === '/runtime-lab/chat')

    expect(route).toBeTruthy()
    expect(route?.meta.runtimeLabChat).toBe(true)
    expect(navItem?.label).toBe('路由对话')
  })
})
