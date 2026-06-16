import { beforeEach, describe, expect, it, vi } from 'vitest'

const requestMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn(),
}))

vi.mock('@/utils/request', () => requestMocks)

describe('provider frontend API client', () => {
  beforeEach(() => {
    requestMocks.get.mockReset()
    requestMocks.post.mockReset()
    requestMocks.put.mockReset()
    requestMocks.del.mockReset()
  })

  it('tests one configured model through the provider model probe endpoint', async () => {
    requestMocks.post.mockResolvedValueOnce({
      ok: true,
      model: 'deepseek/deepseek-v4-flash',
      elapsedMs: 220,
      usage: { inputTokens: 4, outputTokens: 2, totalTokens: 6 },
    })

    const { testProviderModelConnectivity } = await import('./provider')
    const result = await testProviderModelConnectivity(7, 11)

    expect(requestMocks.post).toHaveBeenCalledWith('/v1/providers/7/models/11/connectivity', {})
    expect(result.ok).toBe(true)
  })
})
