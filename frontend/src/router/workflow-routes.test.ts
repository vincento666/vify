// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('workflow module routes', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('exposes workflow and chatflow sibling entries for the module tab shell', async () => {
    const { default: router } = await import('./index')
    const routes = router.getRoutes()
    const paths = routes.map((route) => route.path)
    const workflowRoute = routes.find((route) => route.path === '/workflows')
    const workflowCreateRoute = routes.find((route) => route.path === '/workflows/create')

    expect(paths).toEqual(expect.arrayContaining(['/workflows', '/workflows/create', '/workflow/api-resources', '/chatflows', '/chatflows/create']))
    expect(workflowRoute?.meta.workflowModuleTabs).toEqual([
      { label: '工作流', path: '/workflows', flowType: 'WORKFLOW' },
      { label: '对话流', path: '/chatflows', flowType: 'CHATFLOW' },
    ])
    expect(workflowCreateRoute?.meta.canvasWorkbench).toBe(true)
  })

  it('exposes a Chatflow detail canvas route under the Chatflow module', async () => {
    const { default: router } = await import('./index')
    const routes = router.getRoutes()
    const chatflowDetailRoute = routes.find((route) => route.path === '/chatflows/:id/canvas')

    expect(chatflowDetailRoute).toBeTruthy()
    expect(chatflowDetailRoute?.meta.canvasWorkbench).toBe(true)
    expect(chatflowDetailRoute?.meta.workflowModuleTabs).toEqual([
      { label: '工作流', path: '/workflows', flowType: 'WORKFLOW' },
      { label: '对话流', path: '/chatflows', flowType: 'CHATFLOW' },
    ])
  })
})
