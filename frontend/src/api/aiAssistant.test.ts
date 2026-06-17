import { beforeEach, describe, expect, it, vi } from 'vitest'

const requestMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}))

vi.mock('@/utils/request', () => requestMocks)

describe('ai assistant frontend API client', () => {
  beforeEach(() => {
    requestMocks.get.mockReset()
    requestMocks.post.mockReset()
  })

  it('uses the ai-assistant session message event and approval endpoints', async () => {
    requestMocks.post
      .mockResolvedValueOnce({ id: 10, status: 'ACTIVE' })
      .mockResolvedValueOnce({ runId: 20, status: 'COMPLETED', finalAnswer: 'Echo result' })
      .mockResolvedValueOnce({ id: 7, status: 'APPROVED' })
      .mockResolvedValueOnce({ id: 8, status: 'DENIED' })
    requestMocks.get
      .mockResolvedValueOnce({ list: [{ type: 'run.started' }], total: 1 })
      .mockResolvedValueOnce({ list: [{ id: 7, status: 'PENDING' }], total: 1 })
      .mockResolvedValueOnce({ list: [{ name: 'echo_context' }], total: 1 })
      .mockResolvedValueOnce({ list: [{ id: 20, status: 'COMPLETED' }], total: 1 })
      .mockResolvedValueOnce({ run: { id: 20 }, activeTasks: [], toolCalls: [], approvalQueue: [] })

    const {
      approveAiAssistantApproval,
      createAiAssistantSession,
      denyAiAssistantApproval,
      getAiAssistantRunInspector,
      listAiAssistantApprovals,
      listAiAssistantRunEvents,
      listAiAssistantSessionRuns,
      listAiAssistantTools,
      sendAiAssistantMessage,
    } = await import('./aiAssistant')

    await createAiAssistantSession({ title: 'Kernel' })
    await sendAiAssistantMessage(10, {
      message: 'Echo',
      idempotencyKey: 'front-echo',
      approvalMode: 'smart_approval',
      toolName: 'echo_context',
    })
    await listAiAssistantRunEvents(20)
    await listAiAssistantApprovals()
    await approveAiAssistantApproval(7, { actorId: 'operator-ui' })
    await denyAiAssistantApproval(8, { actorId: 'operator-ui', reason: 'No' })
    await listAiAssistantTools()
    await listAiAssistantSessionRuns(10)
    await getAiAssistantRunInspector(20)

    expect(requestMocks.post).toHaveBeenNthCalledWith(1, '/v1/ai-assistant/sessions', { title: 'Kernel' })
    expect(requestMocks.post).toHaveBeenNthCalledWith(2, '/v1/ai-assistant/sessions/10/messages', {
      message: 'Echo',
      idempotencyKey: 'front-echo',
      approvalMode: 'smart_approval',
      toolName: 'echo_context',
    })
    expect(requestMocks.get).toHaveBeenNthCalledWith(1, '/v1/ai-assistant/runs/20/events')
    expect(requestMocks.get).toHaveBeenNthCalledWith(2, '/v1/ai-assistant/approvals')
    expect(requestMocks.post).toHaveBeenNthCalledWith(3, '/v1/ai-assistant/approvals/7/approve', {
      actorId: 'operator-ui',
    })
    expect(requestMocks.post).toHaveBeenNthCalledWith(4, '/v1/ai-assistant/approvals/8/deny', {
      actorId: 'operator-ui',
      reason: 'No',
    })
    expect(requestMocks.get).toHaveBeenNthCalledWith(3, '/v1/ai-assistant/tools')
    expect(requestMocks.get).toHaveBeenNthCalledWith(4, '/v1/ai-assistant/sessions/10/runs')
    expect(requestMocks.get).toHaveBeenNthCalledWith(5, '/v1/ai-assistant/runs/20/inspector')
  })
})
