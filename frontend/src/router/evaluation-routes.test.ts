// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'

describe('evaluation route', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  it('exposes the Evaluation workbench route', async () => {
    const { default: router } = await import('./index')
    const route = router.getRoutes().find((item) => item.path === '/evaluation')

    expect(route).toBeTruthy()
    expect(route?.meta.defaultEvaluationTab).toBe('experiments')
  })
})
