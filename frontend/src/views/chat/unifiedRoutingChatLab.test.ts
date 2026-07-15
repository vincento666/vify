import { describe, expect, it } from 'vitest'

import {
  AIRLINE_SOP_SCENARIOS,
  buildRuntimeLabBoundScenarios,
  buildRuntimeLabConfigSummary,
  buildRuntimeLabFunnelSummary,
  buildRuntimeLabLocalSettings,
  buildRuntimeLabNodeDebugDetail,
  buildRuntimeLabRouteSettingsPayload,
  buildRuntimeLabRouteOutcome,
  buildRuntimeLabTraceCards,
  buildRuntimeLabTranscriptRow,
  applyRuntimeLabSopStreamFrame,
  finalizeRuntimeLabSopStreamRow,
  formatRuntimeLabElapsed,
  formatRuntimeLabUsage,
  getAirlineSopScenario,
  runtimeLabPendingDelayMs,
} from './unifiedRoutingChatLab'

describe('unified routing chat lab model', () => {
  it('offers the fifteen airline SOP scenarios used by the runtime business gate', () => {
    expect(AIRLINE_SOP_SCENARIOS.map((scenario) => scenario.id)).toEqual([
      'flight_booking',
      'fare_quote',
      'group_booking',
      'ancillary_sales',
      'refund_ticket',
      'change_flight',
      'passenger_info_change',
      'invoice_apply',
      'baggage_service',
      'seat_checkin',
      'flight_status',
      'special_assistance',
      'pet_cabin',
      'irregular_flight',
      'membership_service',
    ])
    expect(getAirlineSopScenario('refund_ticket')?.triggerUtterances).toEqual(
      expect.arrayContaining([
        expect.stringContaining('退掉'),
        expect.stringContaining('票款'),
      ]),
    )
    for (const scenario of AIRLINE_SOP_SCENARIOS) {
      expect(scenario.triggerUtterances.length).toBeGreaterThanOrEqual(3)
      expect('startMessage' in scenario).toBe(false)
    }
  })

  it('summarizes backend route turns without deciding routing in the frontend', () => {
    const row = buildRuntimeLabTranscriptRow({
      reply: '退票流程完成 phone=13800138000 confirm=确认',
      routeDecision: {
        action: 'COMPLETE_TASK',
        reason: 'active SOP completed',
        targetSopId: 'refund_ticket',
      },
      activeTask: null,
      suspendedTasks: [{ id: 3, sopId: 'invoice_apply', status: 'SUSPENDED' }],
      resumeOffer: { taskId: 3, sopId: 'invoice_apply', prompt: '是否继续发票申请？' },
    })

    expect(row.content).toContain('退票流程完成')
    expect(row.routeAction).toBe('COMPLETE_TASK')
    expect(row.taskSummary).toBe('suspended: invoice_apply')
    expect(row.resumePrompt).toContain('继续发票申请')
  })

  it('merges provider chunks before terminal child output without replaying a final response', () => {
    const pending = { id: 'pending-1', role: 'assistant' as const, content: '', pending: true }
    const withFirstChunk = applyRuntimeLabSopStreamFrame(pending, {
      type: 'delta', source: 'provider', sequence: 4, delta: '正在核验',
    })
    const completed = applyRuntimeLabSopStreamFrame(withFirstChunk, {
      type: 'done', source: 'runtime_v2', sequence: 5,
      event: {
        type: 'workflow_run_interrupted',
        payload: { output: { interrupt: { question: '请确认是否继续办理。' } } },
      },
    })

    expect(withFirstChunk.content).toBe('正在核验')
    expect(withFirstChunk.pending).toBe(false)
    expect(completed.content).toBe('正在核验\n\n请确认是否继续办理。')
    expect(finalizeRuntimeLabSopStreamRow({ ...pending }, '请提供手机号。')).toMatchObject({
      content: '请提供手机号。', pending: false,
    })
  })

  it('summarizes runtime config bindings and arbitrator state for display', () => {
    const summary = buildRuntimeLabConfigSummary({
      sopBindings: [
        {
          sopId: 'flight_booking',
          chatflowId: 12,
          chatflowName: '034 RuntimeLab Airline SOP - 机票预订',
          exists: true,
          canvasPath: '/chatflows/12/canvas',
        },
        {
          sopId: 'refund_ticket',
          chatflowId: 13,
          chatflowName: '034 RuntimeLab Airline SOP - 退票办理',
          exists: true,
          canvasPath: '/chatflows/13/canvas',
        },
      ],
      arbitrator: {
        mode: 'llm',
        model: 'qwen/qwen3.5-9b',
        fallbackModel: 'deepseek/deepseek-v4-flash',
        baseUrl: 'https://openrouter.ai/api/v1',
        apiKeyConfigured: true,
        available: true,
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

    expect(summary.bindingLabel).toBe('已绑定 2 个 Chatflow SOP')
    expect(summary.arbitratorLabel).toBe('llm · qwen/qwen3.5-9b / fallback deepseek/deepseek-v4-flash')
    expect(summary.fallbackAgentLabel).toBe('existing_agent · 航空 FAQ 兜底智能体')
    expect(summary.secretLabel).toBe('API Key 已配置')
    expect(summary.bindingRows[0]).toContain('flight_booking')
    expect(summary.bindingRows[0]).toContain('#12')
  })

  it('builds selectable SOPs from backend Chatflow bindings', () => {
    const rows = buildRuntimeLabBoundScenarios({
      sopBindings: [
        {
          sopId: 'flight_booking',
          chatflowId: 12,
          chatflowName: '034 RuntimeLab Airline SOP - 机票预订',
          exists: true,
          canvasPath: '/chatflows/12/canvas',
        },
        {
          sopId: 'custom_irregular',
          chatflowId: 99,
          chatflowName: '自定义异常航班处理',
          exists: true,
          canvasPath: '/chatflows/99/canvas',
        },
      ],
      arbitrator: {
        mode: 'llm',
        model: 'qwen/qwen3.5-9b',
        baseUrl: 'https://openrouter.ai/api/v1',
        apiKeyConfigured: true,
        available: true,
      },
    })

    expect(rows.map((row) => row.id)).toEqual(['flight_booking', 'custom_irregular'])
    expect(rows[0].label).toBe('机票预订')
    expect(rows[0].canvasPath).toBe('/chatflows/12/canvas')
    expect(rows[1].label).toBe('自定义异常航班处理')
  })

  it('builds temporary route lab settings from backend config and defaults', () => {
    const settings = buildRuntimeLabLocalSettings({
      sopBindings: [],
      arbitrator: {
        mode: 'llm',
        model: 'qwen/qwen3.5-9b',
        fallbackModel: 'deepseek/deepseek-v4-flash',
        baseUrl: 'https://openrouter.ai/api/v1',
        apiKeyConfigured: true,
        available: true,
      },
      fallbackAgent: {
        enabled: true,
        type: 'existing_agent',
        agentId: 7,
        agentName: '航空 FAQ 兜底智能体',
        available: true,
      },
      thresholds: {
        classifierMinConfidence: 0.64,
        candidateTopK: 5,
        strongAcceptThreshold: 0.92,
      },
      faq: {
        knowledgeBaseIds: [101],
      },
      rag: {
        knowledgeBaseIds: [201],
      },
    })

    expect(settings.arbitratorMode).toBe('llm')
    expect(settings.arbitratorModelConfigId).toBeNull()
    expect(settings.arbitratorModel).toBe('qwen/qwen3.5-9b')
    expect(settings.fallbackModelConfigId).toBeNull()
    expect(settings.fallbackModel).toBe('deepseek/deepseek-v4-flash')
    expect(settings.temporaryModel.enabled).toBe(false)
    expect(settings.temporaryModel.model).toBe('qwen/qwen3.5-9b')
    expect(settings.temporaryFallbackModel.enabled).toBe(false)
    expect(settings.temporaryFallbackModel.model).toBe('deepseek/deepseek-v4-flash')
    expect(settings.fallbackAgentEnabled).toBe(true)
    expect(settings.fallbackAgentId).toBe(7)
    expect(settings.classifierMinConfidence).toBe(0.64)
    expect(settings.candidateTopK).toBe(5)
    expect(settings.faqKnowledgeBaseIds).toEqual([101])
    expect(settings.ragKnowledgeBaseIds).toEqual([201])

    const payload = buildRuntimeLabRouteSettingsPayload(settings)
    expect(payload.arbitrator.model).toBe('qwen/qwen3.5-9b')
    expect(payload.thresholds.classifierMinConfidence).toBe(0.64)
    expect(payload).not.toHaveProperty('fallbackAgent')
    expect(payload).not.toHaveProperty('faq')
    expect(payload).not.toHaveProperty('rag')
    expect(payload).not.toHaveProperty('handoff')
    expect(payload.arbitrator).not.toHaveProperty('baseUrl')
  })

  it('sends temporary arbitrator model config only when explicitly enabled', () => {
    const settings = buildRuntimeLabLocalSettings({
      sopBindings: [],
      arbitrator: {
        mode: 'llm',
        model: 'qwen/qwen3.5-9b',
        fallbackModel: 'deepseek/deepseek-v4-flash',
        baseUrl: 'https://openrouter.ai/api/v1',
        apiKeyConfigured: true,
        available: true,
      },
    })

    settings.arbitratorModelConfigId = 12
    settings.fallbackModelConfigId = 13
    settings.temporaryModel = {
      enabled: true,
      model: 'temp-main-model',
      baseUrl: 'https://temp.example.test/v1',
      apiKey: 'sk-temp',
      temperature: 0.2,
      maxTokens: 256,
      topP: 0.8,
    }
    settings.temporaryFallbackModel = {
      enabled: true,
      model: 'temp-fallback-model',
      baseUrl: 'https://temp-fallback.example.test/v1',
      apiKey: 'sk-temp-fallback',
      temperature: 0.1,
      maxTokens: 128,
      topP: 0.7,
    }

    const payload = buildRuntimeLabRouteSettingsPayload(settings)

    expect(payload.arbitrator.modelConfigId).toBeNull()
    expect(payload.arbitrator.fallbackModelConfigId).toBeNull()
    expect(payload.arbitrator.temporaryModel).toEqual({
      enabled: true,
      model: 'temp-main-model',
      baseUrl: 'https://temp.example.test/v1',
      apiKey: 'sk-temp',
      temperature: 0.2,
      maxTokens: 256,
      topP: 0.8,
    })
    expect(payload.arbitrator.temporaryFallbackModel?.model).toBe('temp-fallback-model')
  })

  it('summarizes Chatflow trace nodes and slot values for the inspector', () => {
    const cards = buildRuntimeLabTraceCards({
      total: 1,
      tasks: [
        {
          taskId: 7,
          sopId: 'flight_booking',
          status: 'RUNNING',
          currentStep: 'collect',
          chatflow: {
            chatflowId: 12,
            chatflowName: '机票预订',
            exists: true,
            runId: 88,
            eventId: 99,
            checkpointId: 100,
            sessionId: 'session-88',
            canvasPath: '/chatflows/12/canvas',
            debugPath: '/chatflows/12/canvas?runId=88&debug=1',
          },
          nodes: [
            {
              nodeKey: 'start',
              nodeType: 'START',
              name: 'Start',
              status: 'SUCCEEDED',
              current: false,
              elapsedMs: 1,
              inputs: {},
              outputs: {},
              usage: { inputTokens: 0, outputTokens: 0, totalTokens: 0, estimated: false },
              error: '',
            },
            {
              nodeKey: 'collect',
              nodeType: 'INFORMATION_COLLECTION',
              name: '收集信息',
              status: 'WAITING',
              current: true,
              elapsedMs: 12,
              inputs: { rendered: { inputText: '广州飞北京' } },
              outputs: { collected: { route: '广州飞北京' } },
              usage: { inputTokens: 0, outputTokens: 0, totalTokens: 0, estimated: false },
              error: '',
            },
          ],
          edges: [],
          events: [{ id: 1, type: 'interrupt', runId: 88, sequence: 1, nodeKey: 'collect', payload: {}, checkpointId: 100, createdAt: null }],
          variables: {
            businessRefs: { route: '广州飞北京' },
            collected: { route: '广州飞北京' },
            scoped: { 'conversation.route': '广州飞北京' },
            session: {},
          },
        },
      ],
    })

    expect(cards[0].currentNodeLabel).toBe('collect · 收集信息')
    expect(cards[0].completedCountLabel).toBe('1/2 完成')
    expect(cards[0].debugPath).toBe('/chatflows/12/canvas?runId=88&debug=1')
    expect(cards[0].slotRows).toEqual([{ key: 'route', value: '广州飞北京' }])
  })

  it('builds trace cards when currentStep is absent and slots come from aggregator collected', () => {
    const cards = buildRuntimeLabTraceCards({
      total: 1,
      tasks: [
        {
          taskId: 9,
          sopId: 'flight_booking',
          status: 'RUNNING',
          chatflow: {
            chatflowId: 12,
            chatflowName: '机票预订',
            exists: true,
            runId: 88,
            eventId: null,
            checkpointId: 100,
            sessionId: '7777',
            canvasPath: '/chatflows/12/canvas',
            debugPath: '/chatflows/12/canvas?runId=88&debug=1',
          },
          nodes: [
            {
              nodeKey: 'collect',
              nodeType: 'INFORMATION_COLLECTION',
              name: '收集信息',
              status: 'WAITING',
              current: true,
              elapsedMs: 0,
              inputs: {},
              outputs: {},
              usage: { inputTokens: 0, outputTokens: 0, totalTokens: 0, estimated: false },
              error: '',
            },
          ],
          edges: [],
          events: [],
          variables: {
            businessRefs: { route: '广州飞北京' },
            collected: { route: '广州飞北京' },
            scoped: {},
            session: { node_outputs: {} },
          },
        },
      ],
    })

    expect(cards[0].currentNodeLabel).toBe('collect · 收集信息')
    expect(cards[0].slotRows).toEqual([{ key: 'route', value: '广州飞北京' }])
  })

  it('uses business-specific reply samples for flight status completion', () => {
    const flightStatus = getAirlineSopScenario('flight_status')

    expect(flightStatus?.sampleReplies[0]).toContain('航班号')
    expect(flightStatus?.sampleReplies[0]).not.toContain('订单号')
  })

  it('summarizes the funnel stage and LLM arbitration evidence from a route decision', () => {
    const summary = buildRuntimeLabFunnelSummary({
      action: 'START_SOP',
      targetSopId: 'flight_booking',
      reason: 'qwen selected booking from finite candidates',
      candidateSources: ['enabled_scope_fallback'],
      policyGate: { stage: 'post_classifier', decisionAction: 'START_SOP' },
      classifierResult: {
        arbitrator_mode: 'llm',
        used_real_llm: true,
      },
    })

    expect(summary.stageLabel).toBe('post_classifier')
    expect(summary.sourceLabel).toBe('enabled_scope_fallback')
    expect(summary.arbitratorLabel).toBe('llm · real')
  })

  it('builds visible route outcomes for handoff faq clarify and fallback actions', () => {
    expect(
      buildRuntimeLabRouteOutcome({
        action: 'HANDOFF_TO_HUMAN',
        reason: 'Explicit handoff candidate accepted before classifier',
        handoff: { sourceLayer: 'explicit_signal', reasonCode: 'USER_REQUEST' },
      }),
    ).toEqual({
      tone: 'danger',
      title: '转人工',
      detail: 'USER_REQUEST · explicit_signal',
    })

    expect(
      buildRuntimeLabRouteOutcome({
        action: 'ANSWER_FAQ',
        reason: 'FAQ answered',
        faqAnswer: { sourceLayer: 'runtime_airline_faq', reasonCode: 'CHILD_TICKET_REFUND' },
      }),
    ).toEqual({
      tone: 'success',
      title: 'FAQ命中',
      detail: 'CHILD_TICKET_REFUND · runtime_airline_faq',
    })

    expect(buildRuntimeLabRouteOutcome({ action: 'CLARIFY', reason: 'No shallow signal' })!.tone).toBe('warning')
    expect(buildRuntimeLabRouteOutcome({ action: 'AGENT_FALLBACK', reason: 'fallback' })!.title).toBe('兜底回答')
  })

  it('keeps the assistant pending indicator visible long enough to animate', () => {
    expect(runtimeLabPendingDelayMs(1000, 1000)).toBeGreaterThanOrEqual(500)
    expect(runtimeLabPendingDelayMs(1000, 1400)).toBeGreaterThan(0)
    expect(runtimeLabPendingDelayMs(1000, 2000)).toBe(0)
  })

  it('builds assistant debug details from route steps and LLM arbitration usage', () => {
    const row = buildRuntimeLabTranscriptRow(
      {
        reply: '已进入机票预订',
        routeDecision: {
          action: 'START_SOP',
          targetSopId: 'flight_booking',
          reason: 'LLM selected booking',
          policyGate: {
            elapsedMs: 845,
            steps: [
              { id: 'candidate_recall', label: '候选召回', elapsedMs: 3, input: { message: '我要订广州飞北京' }, output: { candidates: 0 } },
              { id: 'llm_intent_arbitration', label: 'LLM有限意图仲裁', elapsedMs: 812, input: { model: 'qwen/qwen3.5-9b' }, output: { selectedIntent: 'flight_booking' } },
            ],
          },
          classifierResult: {
            _debug: {
              model: 'qwen/qwen3.5-9b',
              input: { messages: [{ role: 'user', content: '我要订广州飞北京' }] },
              output: { selectedIntent: 'flight_booking' },
              usage: { prompt_tokens: 128, completion_tokens: 16, total_tokens: 144 },
              elapsedMs: 812,
            },
          },
        },
        activeTask: { id: 8, sopId: 'flight_booking', status: 'RUNNING' },
        suspendedTasks: [],
        resumeOffer: null,
      },
      930,
    )

    expect(row.elapsedMs).toBe(930)
    expect(row.usage?.totalTokens).toBe(144)
    expect(row.debugDetail?.steps.map((step) => step.id)).toContain('llm_intent_arbitration')
    expect(row.debugDetail?.output).toEqual({ selectedIntent: 'flight_booking' })
  })

  it('builds node debug details with inputs outputs timing and usage', () => {
    const card = buildRuntimeLabTraceCards({
      total: 1,
      tasks: [
        {
          taskId: 7,
          sopId: 'flight_booking',
          status: 'RUNNING',
          currentStep: 'llm',
          chatflow: {
            chatflowId: 12,
            chatflowName: '机票预订',
            exists: true,
            runId: 88,
            eventId: 99,
            checkpointId: 100,
            sessionId: 'session-88',
            canvasPath: '/chatflows/12/canvas',
            debugPath: '/chatflows/12/canvas?runId=88&debug=1',
          },
          nodes: [
            {
              nodeKey: 'llm',
              nodeType: 'LLM',
              name: '话术生成',
              status: 'SUCCEEDED',
              current: false,
              elapsedMs: 456,
              inputs: { rendered: { prompt: '帮用户确认预订' } },
              outputs: { answer: '已进入预订', __usage: { inputTokens: 30, outputTokens: 8, totalTokens: 38, estimated: false } },
              usage: { inputTokens: 30, outputTokens: 8, totalTokens: 38, estimated: false },
              error: '',
            },
          ],
          edges: [],
          events: [],
          variables: {
            businessRefs: {},
            collected: {},
            scoped: {},
            session: {},
          },
        },
      ],
    })[0]

    const detail = buildRuntimeLabNodeDebugDetail(card, card.nodes[0])
    expect(detail.title).toBe('llm · 话术生成')
    expect(detail.elapsedMs).toBe(456)
    expect(detail.input).toEqual({ rendered: { prompt: '帮用户确认预订' } })
    expect(formatRuntimeLabUsage(detail.usage)).toBe('in 30 / out 8 / total 38')
    expect(formatRuntimeLabElapsed(detail.elapsedMs)).toBe('456ms')
  })
})
