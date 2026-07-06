import { beforeEach, describe, expect, it, vi } from 'vitest'

const requestMocks = vi.hoisted(() => ({
  del: vi.fn(),
  get: vi.fn(),
  post: vi.fn(),
}))

vi.mock('@/utils/request', () => requestMocks)

describe('ai assistant frontend API client', () => {
  beforeEach(() => {
    requestMocks.del.mockReset()
    requestMocks.get.mockReset()
    requestMocks.post.mockReset()
  })

  it('uses the ai-assistant session message event and approval endpoints', async () => {
    requestMocks.post
      .mockResolvedValueOnce({ id: 10, status: 'ACTIVE' })
      .mockResolvedValueOnce({ runId: 20, status: 'COMPLETED', finalAnswer: 'Echo result' })
      .mockResolvedValueOnce({ runId: 21, status: 'RUNNING', finalAnswer: '', eventStreamRef: '/stream' })
      .mockResolvedValueOnce({ id: 7, status: 'APPROVED' })
      .mockResolvedValueOnce({ id: 8, status: 'DENIED' })
    requestMocks.get
      .mockResolvedValueOnce({ list: [{ type: 'run.started' }], total: 1 })
      .mockResolvedValueOnce({ list: [{ id: 7, status: 'PENDING' }], total: 1 })
      .mockResolvedValueOnce({ list: [{ id: 20, status: 'COMPLETED' }], total: 1 })
      .mockResolvedValueOnce({ run: { id: 20 }, activeTasks: [], toolCalls: [], approvalQueue: [] })
      .mockResolvedValueOnce({ run: { id: 20 }, events: [], streamCursor: { lastSequence: 0 }, inspector: { run: { id: 20 } } })

    const {
      buildAiAssistantMessagePayload,
      approveAiAssistantApproval,
      clearAiAssistantSessionHistory,
      createAiAssistantSession,
      deleteAiAssistantSession,
      denyAiAssistantApproval,
      getAiAssistantRunInspector,
      getAiAssistantRunSnapshot,
      listAiAssistantApprovals,
      listAiAssistantRunEvents,
      listAiAssistantSessionRuns,
      processAiAssistantRunWorker,
      sendAiAssistantMessage,
      startAiAssistantMessage,
    } = await import('./aiAssistant')

    const runtimeConfig = {
      modelName: 'qwen/qwen3.6-27b',
      baseUrl: 'https://openrouter.ai/api/v1',
      apiKey: 'sk-temp',
      temperature: 0.2,
      maxTokens: 4096,
      streamEnabled: true,
    }

    await createAiAssistantSession({ title: 'Kernel' })
    const payload = buildAiAssistantMessagePayload('Echo', runtimeConfig, 'front-echo', 'ask_each_time')
    await sendAiAssistantMessage(10, payload)
    await startAiAssistantMessage(10, buildAiAssistantMessagePayload('Stream Echo', runtimeConfig, 'front-stream'))
    await processAiAssistantRunWorker(21, runtimeConfig)
    await listAiAssistantRunEvents(20)
    await listAiAssistantApprovals()
    await approveAiAssistantApproval(7, { actorId: 'operator-ui' })
    await denyAiAssistantApproval(8, { actorId: 'operator-ui', reason: 'No' })
    await listAiAssistantSessionRuns(10)
    await getAiAssistantRunInspector(20)
    await getAiAssistantRunSnapshot(20, 12)
    await clearAiAssistantSessionHistory(10)
    await deleteAiAssistantSession(10)

    expect(requestMocks.post).toHaveBeenNthCalledWith(1, '/v1/ai-assistant/sessions', { title: 'Kernel' })
    expect(requestMocks.post).toHaveBeenNthCalledWith(2, '/v1/ai-assistant/sessions/10/messages', {
      message: 'Echo',
      idempotencyKey: 'front-echo',
      planningStrategy: 'auto_lightweight',
      approvalMode: 'ask_each_time',
      modelMode: 'live',
      modelConfig: {
        provider: 'openrouter',
        baseUrl: 'https://openrouter.ai/api/v1',
        model: 'qwen/qwen3.6-27b',
        apiKey: 'sk-temp',
        temperature: 0.2,
        maxTokens: 4096,
      },
    })
    expect(requestMocks.post).toHaveBeenNthCalledWith(3, '/v1/ai-assistant/sessions/10/messages/async', {
      message: 'Stream Echo',
      idempotencyKey: 'front-stream',
      planningStrategy: 'auto_lightweight',
      approvalMode: 'smart_approval',
      modelMode: 'live',
      modelConfig: {
        provider: 'openrouter',
        baseUrl: 'https://openrouter.ai/api/v1',
        model: 'qwen/qwen3.6-27b',
        apiKey: 'sk-temp',
        temperature: 0.2,
        maxTokens: 4096,
      },
    })
    expect(requestMocks.post).toHaveBeenNthCalledWith(4, '/v1/ai-assistant/runs/21/worker/process', {
      modelConfig: {
        provider: 'openrouter',
        baseUrl: 'https://openrouter.ai/api/v1',
        model: 'qwen/qwen3.6-27b',
        apiKey: 'sk-temp',
        temperature: 0.2,
        maxTokens: 4096,
      },
    })
    expect(requestMocks.get).toHaveBeenNthCalledWith(1, '/v1/ai-assistant/runs/20/events', undefined)
    expect(requestMocks.get).toHaveBeenNthCalledWith(2, '/v1/ai-assistant/approvals')
    expect(requestMocks.post).toHaveBeenNthCalledWith(5, '/v1/ai-assistant/approvals/7/approve', {
      actorId: 'operator-ui',
    })
    expect(requestMocks.post).toHaveBeenNthCalledWith(6, '/v1/ai-assistant/approvals/8/deny', {
      actorId: 'operator-ui',
      reason: 'No',
    })
    expect(requestMocks.get).toHaveBeenNthCalledWith(3, '/v1/ai-assistant/sessions/10/runs')
    expect(requestMocks.get).toHaveBeenNthCalledWith(4, '/v1/ai-assistant/runs/20/inspector')
    expect(requestMocks.get).toHaveBeenNthCalledWith(5, '/v1/ai-assistant/runs/20/snapshot', { afterSequence: 12 })
    expect(requestMocks.del).toHaveBeenNthCalledWith(1, '/v1/ai-assistant/sessions/10/history')
    expect(requestMocks.del).toHaveBeenNthCalledWith(2, '/v1/ai-assistant/sessions/10')
  })

  it('defaults to smart approval but allows the composer to choose a stricter permission mode', async () => {
    const { buildAiAssistantMessagePayload } = await import('./aiAssistant')
    const runtimeConfig = {
      modelName: 'qwen/qwen3.6-27b',
      baseUrl: 'https://openrouter.ai/api/v1',
      apiKey: 'sk-temp',
      temperature: 0.2,
      maxTokens: 4096,
      streamEnabled: true,
    }

    expect(buildAiAssistantMessagePayload('默认', runtimeConfig, 'default').approvalMode).toBe('smart_approval')
    expect(buildAiAssistantMessagePayload('请求审批', runtimeConfig, 'strict', 'ask_each_time').approvalMode).toBe(
      'ask_each_time',
    )
    expect(buildAiAssistantMessagePayload('完全访问', runtimeConfig, 'full', 'always_approve').approvalMode).toBe(
      'always_approve',
    )
  })

  it('allows deterministic runtime mode without live provider config', async () => {
    const { buildAiAssistantMessagePayload } = await import('./aiAssistant')
    const runtimeConfig = {
      modelMode: 'deterministic',
      modelName: 'qwen/qwen3.6-27b',
      baseUrl: 'https://openrouter.ai/api/v1',
      apiKey: '',
      temperature: 0.2,
      maxTokens: 4096,
      streamEnabled: true,
    }

    expect(buildAiAssistantMessagePayload('本地', runtimeConfig, 'local')).toEqual({
      message: '本地',
      idempotencyKey: 'local',
      planningStrategy: 'auto_lightweight',
      approvalMode: 'smart_approval',
      modelMode: 'deterministic',
    })
  })
})
