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
      resumeRuntimeV2Run,
      cancelRuntimeV2Run,
      runChatflowV2,
      runWorkflowV2,
    } = await import('./workflow')

    await runWorkflowV2(12, { USER_INPUT: 'hello' }, 'workflow-key')
    await runChatflowV2(21, { message: 'hello' }, 'chatflow-key')
    await resumeRuntimeV2Run(701, { resumeData: { answer: 'refund' }, idempotencyKey: 'resume-key' })
    await cancelRuntimeV2Run(701)
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
    expect(requestMocks.post).toHaveBeenNthCalledWith(3, '/v1/runtime-runs/701/resume', {
      resumeData: { answer: 'refund' },
      idempotencyKey: 'resume-key',
    })
    expect(requestMocks.post).toHaveBeenNthCalledWith(4, '/v1/runtime-runs/701/cancel', {})
    expect(requestMocks.get).toHaveBeenNthCalledWith(1, '/v1/runtime-runs/701')
    expect(requestMocks.get).toHaveBeenNthCalledWith(2, '/v1/runtime-runs/701/events', { afterSequence: 4 })
    expect(requestMocks.get).toHaveBeenNthCalledWith(3, '/v1/runtime-runs/701/nodes')
  })

  it('passes explicit published version ids when starting runtime v2 runs', async () => {
    requestMocks.post.mockResolvedValueOnce({ runId: 801, versionId: 41 }).mockResolvedValueOnce({ runId: 802, versionId: 42 })

    const {
      runChatflowV2,
      runWorkflowV2,
    } = await import('./workflow')

    await runWorkflowV2(12, { USER_INPUT: 'historical' }, 'workflow-version-key', 41)
    await runChatflowV2(21, { message: 'historical' }, 'chatflow-version-key', 42)

    expect(requestMocks.post).toHaveBeenNthCalledWith(1, '/v1/workflows/12/runs-v2', {
      input: { USER_INPUT: 'historical' },
      idempotencyKey: 'workflow-version-key',
      versionId: 41,
    })
    expect(requestMocks.post).toHaveBeenNthCalledWith(2, '/v1/chatflows/21/runs-v2', {
      input: { message: 'historical' },
      idempotencyKey: 'chatflow-version-key',
      versionId: 42,
    })
  })

  it('passes silent error options only when requested', async () => {
    requestMocks.post.mockResolvedValueOnce({ runId: 901 }).mockResolvedValueOnce({ runId: 902 })

    const {
      runChatflowV2,
      runWorkflowV2,
    } = await import('./workflow')

    await runWorkflowV2(12, { USER_INPUT: 'fallback probe' }, 'workflow-silent-key', undefined, { silentError: true })
    await runChatflowV2(21, { message: 'fallback probe' }, 'chatflow-silent-key', undefined, { silentError: true })

    expect(requestMocks.post).toHaveBeenNthCalledWith(1, '/v1/workflows/12/runs-v2', {
      input: { USER_INPUT: 'fallback probe' },
      idempotencyKey: 'workflow-silent-key',
    }, { silentError: true })
    expect(requestMocks.post).toHaveBeenNthCalledWith(2, '/v1/chatflows/21/runs-v2', {
      input: { message: 'fallback probe' },
      idempotencyKey: 'chatflow-silent-key',
    }, { silentError: true })
  })
})
