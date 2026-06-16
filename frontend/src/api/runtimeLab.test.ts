import { beforeEach, describe, expect, it, vi } from 'vitest'

const requestMocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
}))

vi.mock('@/utils/request', () => requestMocks)

describe('runtime-lab frontend API client', () => {
  beforeEach(() => {
    requestMocks.get.mockReset()
    requestMocks.post.mockReset()
    requestMocks.put.mockReset()
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
        routeSettings: {
          thresholds: {
            classifierMinConfidence: 0.72,
            candidateTopK: 3,
          },
        },
      }),
    ).resolves.toEqual({ reply: '请提供退票办理手机号。' })

    expect(requestMocks.post).toHaveBeenNthCalledWith(1, '/v1/runtime-lab/sessions')
    expect(requestMocks.post).toHaveBeenNthCalledWith(2, '/v1/runtime-lab/sessions/12/messages', {
      message: '我要退票',
      idempotencyKey: 'front-red',
      routeSettings: {
        thresholds: {
          classifierMinConfidence: 0.72,
          candidateTopK: 3,
        },
      },
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

  it('loads runtime-lab routing configuration without secrets', async () => {
    requestMocks.get.mockResolvedValueOnce({
      sopBindings: [
        {
          sopId: 'flight_booking',
          chatflowId: 12,
          chatflowName: '034 RuntimeLab Airline SOP - 机票预订',
          exists: true,
          canvasPath: '/chatflows/12/canvas',
        },
      ],
      arbitrator: {
        mode: 'llm',
        model: 'qwen/qwen3.5-9b',
        baseUrl: 'https://openrouter.ai/api/v1',
        apiKeyConfigured: true,
      },
      fallbackAgent: {
        enabled: true,
        type: 'existing_agent',
        agentId: 7,
        agentName: '航空 FAQ 兜底智能体',
        available: true,
      },
      fallbackAgentOptions: [
        { id: 7, name: '航空 FAQ 兜底智能体', description: '', enabled: true },
      ],
    })

    const { getRuntimeLabConfig } = await import('./runtimeLab')
    const config = await getRuntimeLabConfig()

    expect(requestMocks.get).toHaveBeenCalledWith('/v1/runtime-lab/config')
    expect(config.arbitrator.model).toBe('qwen/qwen3.5-9b')
    expect(config.fallbackAgent?.agentName).toBe('航空 FAQ 兜底智能体')
    expect(config.fallbackAgentOptions?.[0]?.id).toBe(7)
    expect(JSON.stringify(config)).not.toContain('sk-')
  })

  it('updates the runtime-lab fallback Agent selection', async () => {
    requestMocks.put.mockResolvedValueOnce({
      fallbackAgent: {
        enabled: true,
        type: 'existing_agent',
        agentId: 7,
        agentName: '航空 FAQ 兜底智能体',
        available: true,
      },
    })

    const { updateRuntimeLabFallbackAgent } = await import('./runtimeLab')
    const result = await updateRuntimeLabFallbackAgent({ enabled: true, agentId: 7 })

    expect(requestMocks.put).toHaveBeenCalledWith('/v1/runtime-lab/fallback-agent', {
      enabled: true,
      agentId: 7,
    })
    expect(result.fallbackAgent.agentId).toBe(7)
  })

  it('loads Chatflow trace for the runtime-lab inspector', async () => {
    requestMocks.get.mockResolvedValueOnce({ tasks: [], total: 0 })

    const { getRuntimeLabChatflowTrace } = await import('./runtimeLab')
    const trace = await getRuntimeLabChatflowTrace(18)

    expect(requestMocks.get).toHaveBeenCalledWith('/v1/runtime-lab/sessions/18/chatflow-trace')
    expect(trace.total).toBe(0)
  })

  it('tests a temporary route LLM model through the backend probe endpoint', async () => {
    requestMocks.post.mockResolvedValueOnce({ ok: true, model: 'qwen/qwen3.5-9b', elapsedMs: 120 })

    const { testRuntimeLabTemporaryModel } = await import('./runtimeLab')
    const result = await testRuntimeLabTemporaryModel({
      model: 'qwen/qwen3.5-9b',
      baseUrl: 'https://openrouter.ai/api/v1',
      apiKey: 'sk-test',
      temperature: 0,
      maxTokens: 8,
      topP: 1,
    })

    expect(requestMocks.post).toHaveBeenCalledWith('/v1/runtime-lab/route-model/connectivity', {
      model: 'qwen/qwen3.5-9b',
      baseUrl: 'https://openrouter.ai/api/v1',
      apiKey: 'sk-test',
      temperature: 0,
      maxTokens: 8,
      topP: 1,
    })
    expect(result.ok).toBe(true)
  })
})
