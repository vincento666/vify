import { describe, expect, it } from 'vitest'

import {
  AIRLINE_SOP_SCENARIOS,
  buildRuntimeLabBoundScenarios,
  buildRuntimeLabConfigSummary,
  buildRuntimeLabFunnelSummary,
  buildRuntimeLabTraceCards,
  buildRuntimeLabTranscriptRow,
  getAirlineSopScenario,
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
        baseUrl: 'https://openrouter.ai/api/v1',
        apiKeyConfigured: true,
        available: true,
      },
    })

    expect(summary.bindingLabel).toBe('已绑定 2 个 Chatflow SOP')
    expect(summary.arbitratorLabel).toBe('llm · qwen/qwen3.5-9b')
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
            { nodeKey: 'start', nodeType: 'START', name: 'Start', status: 'SUCCEEDED', current: false, elapsedMs: 1, outputs: {}, error: '' },
            { nodeKey: 'collect', nodeType: 'INFORMATION_COLLECTION', name: '收集信息', status: 'WAITING', current: true, elapsedMs: 12, outputs: { collected: { route: '广州飞北京' } }, error: '' },
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
})
