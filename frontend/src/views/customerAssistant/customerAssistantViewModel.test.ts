import { describe, expect, it } from 'vitest'

import type { CustomerAssistantProposedAction } from '@/api/customerAssistant'

import {
  mockCustomerAssistantEvents,
  mockCustomerAssistantMetrics,
  mockCustomerAssistantTasks,
  mockCustomerAssistantTurnResult,
} from './customerAssistantFixtures'
import {
  applyCustomerAssistantActionState,
  buildCustomerAssistantState,
  formatCustomerAssistantActionReceipt,
  formatCustomerAssistantEvents,
  formatCustomerAssistantMetrics,
  formatOperatorAdvisoryEvidence,
  formatTaskRecognitionEvidence,
  summarizeCustomerAssistantTasks,
} from './customerAssistantViewModel'

describe('customer assistant view model', () => {
  it('normalizes customer and operator lanes without mixing internal controls into the customer lane', () => {
    const state = buildCustomerAssistantState({
      sessionId: 12,
      customerInput: '我要退票',
      operatorInput: '请给我处置建议',
      turnResult: mockCustomerAssistantTurnResult,
    })

    expect(state.customerMessages.map((item) => item.role)).toEqual(['customer', 'draft'])
    expect(state.customerMessages[0]).toMatchObject({
      lane: 'customer',
      content: '我要退票',
      source: 'customer',
      pending: false,
    })
    expect(state.customerMessages[1]).toMatchObject({
      lane: 'customer',
      content: mockCustomerAssistantTurnResult.customerReplyDraft,
      source: 'assistant-draft',
      pending: true,
    })
    expect(state.customerMessages.every((item) => item.controls.length === 0)).toBe(true)

    expect(state.operatorMessages.map((item) => item.role)).toEqual(['operator', 'assistant'])
    expect(state.operatorMessages[1]).toMatchObject({
      lane: 'operator',
      content: mockCustomerAssistantTurnResult.operatorRecommendation,
      source: 'assistant',
    })
  })

  it('summarizes task statuses, missing fields, and display names', () => {
    const summary = summarizeCustomerAssistantTasks(mockCustomerAssistantTasks.list)

    expect(summary.counts).toEqual({ WAITING: 1 })
    expect(summary.items[0]).toMatchObject({
      displayName: '退票处理',
      taskKey: 'refund_ticket',
      status: 'WAITING',
      statusTone: 'warning',
      workerType: 'chatflow_sop',
      missingFields: ['订单号'],
    })
  })

  it('attaches configured worker profile metadata to task rows', () => {
    const summary = summarizeCustomerAssistantTasks(mockCustomerAssistantTasks.list, [
      {
        profileId: 'refund_ticket_chatflow',
        taskKey: 'refund_ticket',
        taskType: 'REFUND',
        workerType: 'chatflow_sop',
        workerRef: 'flight_refund',
        modelPolicyRef: 'customer_assistant_chatflow_default',
        promptRef: 'refund_ticket_sop_prompt',
        toolRefs: ['refund_policy_lookup'],
        riskPolicyRef: 'manual_confirm',
        enabled: true,
      },
    ])

    expect(summary.items[0].profile).toEqual({
      profileId: 'refund_ticket_chatflow',
      modelPolicyRef: 'customer_assistant_chatflow_default',
      promptRef: 'refund_ticket_sop_prompt',
      toolRefs: ['refund_policy_lookup'],
      riskPolicyRef: 'manual_confirm',
    })
  })

  it('matches worker profiles for business-scoped task keys', () => {
    const summary = summarizeCustomerAssistantTasks(
      [
        {
          ...mockCustomerAssistantTasks.list[0],
          taskKey: 'refund_ticket:MU5137-8899',
          workerRef: 'refund_ticket',
        },
      ],
      [
        {
          profileId: 'refund_ticket_chatflow',
          taskKey: 'refund_ticket',
          taskType: 'REFUND',
          workerType: 'chatflow_sop',
          workerRef: 'refund_ticket',
          modelPolicyRef: 'customer_assistant_chatflow_default',
          promptRef: 'refund_ticket_sop_prompt',
          toolRefs: ['refund_policy_lookup'],
          riskPolicyRef: 'manual_confirm',
          enabled: true,
        },
      ],
    )

    expect(summary.items[0].profile?.profileId).toBe('refund_ticket_chatflow')
  })

  it('derives permitted operator task controls from task status', () => {
    const summary = summarizeCustomerAssistantTasks([
      { ...mockCustomerAssistantTasks.list[0], id: 1, status: 'RUNNING' },
      { ...mockCustomerAssistantTasks.list[0], id: 2, status: 'WAITING' },
      { ...mockCustomerAssistantTasks.list[0], id: 3, status: 'FAILED' },
      { ...mockCustomerAssistantTasks.list[0], id: 4, status: 'COMPLETED' },
    ])

    expect(summary.items.map((item) => item.availableControls)).toEqual([
      ['cancel'],
      ['resume', 'cancel'],
      ['retry'],
      [],
    ])
  })

  it('projects durable worker async refs onto running task rows', () => {
    const summary = summarizeCustomerAssistantTasks([
      {
        ...mockCustomerAssistantTasks.list[0],
        status: 'RUNNING',
        lastResult: {
          workerAsyncRefs: {
            supported: true,
            workerRunId: 'customer-assistant-worker-run-42',
            workerStatusRef: '/api/v1/customer-assistant/worker-runs/customer-assistant-worker-run-42',
            workerEventsRef: '/api/v1/customer-assistant/worker-runs/customer-assistant-worker-run-42/events',
            workerResultRef: '/api/v1/customer-assistant/worker-runs/customer-assistant-worker-run-42/result',
            workerEventStreamRef: '/api/v1/customer-assistant/worker-runs/customer-assistant-worker-run-42/events/stream',
          },
        },
      },
    ])

    expect(summary.items[0].workerAsyncRefs?.supported).toBe(true)
    expect(summary.items[0].workerAsyncRefs?.workerRunId).toBe('customer-assistant-worker-run-42')
    expect(summary.items[0].workerAsyncRefs?.workerEventsRef).toBe(
      '/api/v1/customer-assistant/worker-runs/customer-assistant-worker-run-42/events',
    )
  })

  it('keeps recommendation and customer draft as separate operator panel state', () => {
    const state = buildCustomerAssistantState({
      sessionId: 12,
      turnResult: mockCustomerAssistantTurnResult,
    })

    expect(state.recommendation.operatorRecommendation).toContain('refund_ticket worker')
    expect(state.recommendation.customerReplyDraft).toBe(mockCustomerAssistantTurnResult.customerReplyDraft)
    expect(state.recommendation.customerReplyDraft).not.toBe(state.recommendation.operatorRecommendation)
    expect(state.recommendation.warnings).toEqual(['缺少订单号时不可提交退票动作。'])
  })

  it('updates proposed action state immutably from confirm/reject API responses', () => {
    const state = buildCustomerAssistantState({
      sessionId: 12,
      turnResult: mockCustomerAssistantTurnResult,
    })
    const confirmed: CustomerAssistantProposedAction = {
      ...mockCustomerAssistantTurnResult.proposedActions[0],
      status: 'CONFIRMED',
    }

    const updated = applyCustomerAssistantActionState(state, confirmed)

    expect(state.proposedActions[0].status).toBe('PENDING')
    expect(updated.proposedActions[0]).toMatchObject({
      id: confirmed.id,
      status: 'CONFIRMED',
      title: '提交退票申请',
    })
  })

  it('formats executed proposed action receipts with sanitized audit values', () => {
    const action: CustomerAssistantProposedAction = {
      ...mockCustomerAssistantTurnResult.proposedActions[0],
      status: 'EXECUTED',
      result: {
        executorRef: 'refund_submit_mock',
        audit: {
          semanticCode: 'REFUND_SUBMITTED_MOCK',
          orderNo: '[REDACTED]',
          executedAt: '2026-06-17T05:00:00',
        },
        error: null,
      },
    }

    const receipt = formatCustomerAssistantActionReceipt(action)

    expect(receipt).toMatchObject({
      visible: true,
      executorRef: 'refund_submit_mock',
      semanticCode: 'REFUND_SUBMITTED_MOCK',
      executedAt: '2026-06-17T05:00:00',
      error: '',
    })
    expect(receipt.auditRows).toContainEqual({ key: 'orderNo', label: 'orderNo', value: '[REDACTED]' })
    expect(JSON.stringify(receipt)).not.toContain('TK-100')
  })

  it('formats runtime events as compact operator timeline rows', () => {
    const rows = formatCustomerAssistantEvents(mockCustomerAssistantEvents.list)

    expect(rows[0]).toMatchObject({
      key: 'event-501',
      sequenceLabel: '#1',
      title: 'run_started',
      visibilityLabel: 'normal',
      payloadPreview: '{"message":"我要退票"}',
    })
  })

  it('formats task recognition evidence without exposing raw customer text', () => {
    const rows = formatTaskRecognitionEvidence([
      {
        id: 502,
        sessionId: 12,
        runId: 31,
        sequence: 2,
        type: 'task_recognized',
        visibility: 'normal',
        source: 'task_recognition',
        actor: 'customer',
        payload: {
          actor: 'customer',
          message: '客户手机号 13800138000，需要退票',
          commands: [
            {
              taskKey: 'refund_ticket',
              taskType: 'REFUND',
              workerType: 'chatflow_sop',
              workerRef: 'flight_refund',
              profileRefs: {
                profileId: 'refund_ticket_chatflow',
                modelPolicyRef: 'customer_assistant_chatflow_default',
                promptRef: 'refund_ticket_sop_prompt',
                toolRefs: ['refund_policy_lookup'],
                riskPolicyRef: 'manual_confirm',
              },
            },
          ],
        },
      },
    ])

    expect(rows).toEqual([
      {
        key: 'recognition-502-0',
        sequenceLabel: '#2',
        taskKey: 'refund_ticket',
        taskType: 'REFUND',
        workerRoute: 'chatflow_sop · flight_refund',
        profileId: 'refund_ticket_chatflow',
        modelPolicyRef: 'customer_assistant_chatflow_default',
        promptRef: 'refund_ticket_sop_prompt',
        toolRefs: ['refund_policy_lookup'],
        riskPolicyRef: 'manual_confirm',
      },
    ])
    expect(JSON.stringify(rows)).not.toContain('13800138000')
  })

  it('includes recognition evidence in the built operator state', () => {
    const state = buildCustomerAssistantState({
      sessionId: 12,
      events: [
        {
          id: 502,
          sessionId: 12,
          sequence: 2,
          type: 'task_recognized',
          payload: {
            commands: [
              {
                taskKey: 'refund_ticket',
                taskType: 'REFUND',
                workerType: 'chatflow_sop',
                workerRef: 'flight_refund',
                profileRefs: {
                  profileId: 'refund_ticket_chatflow',
                  modelPolicyRef: 'customer_assistant_chatflow_default',
                  promptRef: 'refund_ticket_sop_prompt',
                  toolRefs: ['refund_policy_lookup'],
                  riskPolicyRef: 'manual_confirm',
                },
              },
            ],
          },
        },
      ],
    })

    expect(state.recognitionEvidence[0]).toMatchObject({
      taskKey: 'refund_ticket',
      profileId: 'refund_ticket_chatflow',
    })
  })

  it('formats operator advisory evidence without exposing raw customer context', () => {
    const rows = formatOperatorAdvisoryEvidence([
      {
        id: 601,
        sessionId: 12,
        runId: 41,
        sequence: 9,
        type: 'operator_advisory_context_packed',
        source: 'operator_advisory',
        actor: 'operator',
        payload: {
          turnMode: 'operator_recommendation',
          taskCount: 2,
          eventCount: 8,
          evidenceCount: 2,
          knowledgeSnippetCount: 1,
          message: '客户手机号 13800138000，订单 TK-100',
          warnings: ['Harness advisory summaries unavailable for operator advisory context.'],
        },
      },
    ])

    expect(rows).toEqual([
      {
        key: 'advisory-601',
        sequenceLabel: '#9',
        turnMode: 'operator_recommendation',
        taskCount: 2,
        eventCount: 8,
        evidenceCount: 2,
        knowledgeSnippetCount: 1,
        warnings: ['Harness advisory summaries unavailable for operator advisory context.'],
      },
    ])
    expect(JSON.stringify(rows)).not.toContain('13800138000')
    expect(JSON.stringify(rows)).not.toContain('TK-100')
  })

  it('includes operator advisory evidence in the built operator state', () => {
    const state = buildCustomerAssistantState({
      sessionId: 12,
      events: [
        {
          id: 601,
          sessionId: 12,
          sequence: 9,
          type: 'operator_advisory_context_packed',
          payload: {
            turnMode: 'operator_recommendation',
            taskCount: 2,
            eventCount: 8,
            evidenceCount: 2,
            knowledgeSnippetCount: 1,
            warnings: [],
          },
        },
      ],
    })

    expect(state.operatorAdvisoryEvidence[0]).toMatchObject({
      taskCount: 2,
      knowledgeSnippetCount: 1,
    })
  })

  it('formats session metrics as compact operator tiles and redacted failure rows', () => {
    const metrics = formatCustomerAssistantMetrics({
      ...mockCustomerAssistantMetrics,
      taskStatusCounts: { RUNNING: 2, FAILED: 1 },
      proposedActionStatusCounts: { PENDING: 1, CONFIRMED: 1, EXECUTED: 1 },
      humanConfirmation: { pending: 1, adopted: 2, terminal: 2, adoptionRate: 1 },
      eventCounts: { total: 8, byType: { task_failed: 1 }, bySource: { chatflow_sop: 3 } },
      workerEventCounts: { total: 4, byType: { worker_started: 2 } },
      recentFailureReasons: [
        { taskId: 3, taskType: 'REFUND', source: 'chatflow_sop', reason: '工具失败 [REDACTED] api_key=***' },
      ],
    })

    expect(metrics.tiles).toEqual([
      { key: 'adoption', label: '人工采纳率', value: '100%', tone: 'success' },
      { key: 'pending', label: '待确认动作', value: '1', tone: 'warning' },
      { key: 'tasks', label: '活跃任务', value: '2', tone: 'processing' },
      { key: 'events', label: '运行事件', value: '8', tone: 'default' },
    ])
    expect(metrics.failures[0]).toMatchObject({
      taskType: 'REFUND',
      source: 'chatflow_sop',
      reason: '工具失败 [REDACTED] api_key=***',
    })
  })

  it('formats empty metrics safely before a session exists', () => {
    const metrics = formatCustomerAssistantMetrics(null)

    expect(metrics.empty).toBe(true)
    expect(metrics.tiles[0]).toMatchObject({ key: 'adoption', value: '0%' })
    expect(metrics.failures).toEqual([])
  })

  it('derives live progress stages from L1 events', () => {
    const state = buildCustomerAssistantState({
      sessionId: 12,
      events: [
        { id: 1, sessionId: 12, sequence: 1, type: 'run_started', payload: {} },
        { id: 2, sessionId: 12, sequence: 2, type: 'task_recognized', payload: {} },
        { id: 3, sessionId: 12, sequence: 3, type: 'worker_started', payload: { taskKey: 'refund_ticket' } },
        { id: 4, sessionId: 12, sequence: 4, type: 'recommendation_started', payload: {} },
      ],
    })

    expect(state.progressStages).toEqual([
      { key: 'recognizing', label: 'Recognizing tasks', status: 'complete' },
      { key: 'workers', label: 'Running workers', status: 'complete' },
      { key: 'recommendation', label: 'Generating recommendation', status: 'active' },
      { key: 'ready', label: 'Ready for operator', status: 'pending' },
    ])
  })
})
