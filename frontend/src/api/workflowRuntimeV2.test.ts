import { beforeEach, describe, expect, it, vi } from 'vitest'

const requestMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}))

vi.mock('@/utils/request', () => requestMocks)

describe('workflow runtime v2 frontend API client', () => {
  beforeEach(() => {
    requestMocks.get.mockReset()
    requestMocks.post.mockReset()
  })

  it('uses async runtime v2 start, status, event, and node endpoints', async () => {
    requestMocks.post.mockResolvedValueOnce({ runId: 701 }).mockResolvedValueOnce({ runId: 702 })
    requestMocks.get
      .mockResolvedValueOnce({ runId: 701, status: 'RUNNING' })
      .mockResolvedValueOnce({ list: [], total: 0 })
      .mockResolvedValueOnce({ list: [], total: 0 })

    const {
      getRuntimeV2Run,
      listRuntimeV2Events,
      listRuntimeV2Nodes,
      runChatflowV2,
      runWorkflowV2,
    } = await import('./workflow')

    await runWorkflowV2(12, { USER_INPUT: 'hello' }, 'workflow-key')
    await runChatflowV2(21, { message: 'hello' }, 'chatflow-key')
    await getRuntimeV2Run(701)
    await listRuntimeV2Events(701, { afterSequence: 4 })
    await listRuntimeV2Nodes(701)

    expect(requestMocks.post).toHaveBeenNthCalledWith(1, '/v1/workflows/12/runs-v2', {
      input: { USER_INPUT: 'hello' },
      idempotencyKey: 'workflow-key',
    })
    expect(requestMocks.post).toHaveBeenNthCalledWith(2, '/v1/chatflows/21/runs-v2', {
      input: { message: 'hello' },
      idempotencyKey: 'chatflow-key',
    })
    expect(requestMocks.get).toHaveBeenNthCalledWith(1, '/v1/runtime-runs/701')
    expect(requestMocks.get).toHaveBeenNthCalledWith(2, '/v1/runtime-runs/701/events', { afterSequence: 4 })
    expect(requestMocks.get).toHaveBeenNthCalledWith(3, '/v1/runtime-runs/701/nodes')
  })
})
