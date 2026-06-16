// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('agent workbench routes', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('exposes create and edit workbench routes while keeping the legacy list route', async () => {
    const { default: router } = await import('./index')
    const routes = router.getRoutes()
    const paths = routes.map((route) => route.path)
    const createRoute = routes.find((route) => route.path === '/agents/new')
    const editRoute = routes.find((route) => route.path === '/agents/:id/workbench')

    expect(paths).toEqual(expect.arrayContaining(['/agent', '/agents/new', '/agents/:id/workbench']))
    expect(createRoute?.meta.agentWorkbench).toBe(true)
    expect(editRoute?.meta.agentWorkbench).toBe(true)
  })
})
