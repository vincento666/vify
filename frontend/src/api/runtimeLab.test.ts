import { beforeEach, describe, expect, it, vi } from 'vitest'

const requestMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}))

vi.mock('@/utils/request', () => requestMocks)

describe('runtime-lab frontend API client', () => {
  beforeEach(() => {
    requestMocks.get.mockReset()
    requestMocks.post.mockReset()
  })

  it('uses the runtime-lab session and message endpoints', async () => {
    requestMocks.post
      .mockResolvedValueOnce({ id: 12 })
      .mockResolvedValueOnce({ reply: '请提供退票办理手机号。' })

    const { createRuntimeLabSession, postRuntimeLabMessage } = await import('./runtimeLab')

    await expect(createRuntimeLabSession()).resolves.toEqual({ id: 12 })
    await expect(
      postRuntimeLabMessage(12, {
        message: '我要退票',
        idempotencyKey: 'front-red',
      }),
    ).resolves.toEqual({ reply: '请提供退票办理手机号。' })

    expect(requestMocks.post).toHaveBeenNthCalledWith(1, '/v1/runtime-lab/sessions')
    expect(requestMocks.post).toHaveBeenNthCalledWith(2, '/v1/runtime-lab/sessions/12/messages', {
      message: '我要退票',
      idempotencyKey: 'front-red',
    })
  })

  it('lists runtime-lab task and event ledgers', async () => {
    requestMocks.get.mockResolvedValueOnce({ list: [], total: 0 }).mockResolvedValueOnce({ list: [], total: 0 })

    const { listRuntimeLabEvents, listRuntimeLabTasks } = await import('./runtimeLab')

    await listRuntimeLabTasks(7)
    await listRuntimeLabEvents(7)

    expect(requestMocks.get).toHaveBeenNthCalledWith(1, '/v1/runtime-lab/sessions/7/tasks')
    expect(requestMocks.get).toHaveBeenNthCalledWith(2, '/v1/runtime-lab/sessions/7/events')
  })
})
