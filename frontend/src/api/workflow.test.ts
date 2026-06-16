import { beforeEach, describe, expect, it, vi } from 'vitest'

const requestMocks = vi.hoisted(() => ({
  del: vi.fn(),
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}))

vi.mock('@/utils/request', () => requestMocks)

describe('workflow API client', () => {
  beforeEach(() => {
    requestMocks.del.mockReset()
    requestMocks.get.mockReset()
    requestMocks.post.mockReset()
    requestMocks.put.mockReset()
  })

  it('runs published workflow versions with an optional target version id', async () => {
    requestMocks.post.mockResolvedValueOnce({ runId: 31, versionId: 9 })

    const { runPublishedWorkflow } = await import('./workflow')

    await expect(runPublishedWorkflow(7, { query: 'demo' }, 9)).resolves.toEqual({ runId: 31, versionId: 9 })
    expect(requestMocks.post).toHaveBeenCalledWith('/v1/workflows/7/published-runs', {
      input: { query: 'demo' },
      versionId: 9,
    })
  })

  it('runs active published workflow versions when no version id is provided', async () => {
    requestMocks.post.mockResolvedValueOnce({ runId: 32, version: 2 })

    const { runPublishedWorkflow } = await import('./workflow')

    await runPublishedWorkflow(7, { query: 'demo' })
    expect(requestMocks.post).toHaveBeenCalledWith('/v1/workflows/7/published-runs', {
      input: { query: 'demo' },
    })
  })

  it('runs published chatflow versions with an optional target version id', async () => {
    requestMocks.post.mockResolvedValueOnce({ runId: 33, versionId: 11 })

    const { runPublishedChatflow } = await import('./workflow')

    await expect(runPublishedChatflow(8, { query: 'hello' }, 11)).resolves.toEqual({ runId: 33, versionId: 11 })
    expect(requestMocks.post).toHaveBeenCalledWith('/v1/chatflows/8/published-runs', {
      input: { query: 'hello' },
      versionId: 11,
    })
  })
})
