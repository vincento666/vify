import { describe, expect, it } from 'vitest'

import type { CustomerAssistantProposedAction } from '@/api/customerAssistant'

import {
  mockCustomerAssistantEvents,
  mockCustomerAssistantTasks,
  mockCustomerAssistantTurnResult,
} from './customerAssistantFixtures'
import {
  applyCustomerAssistantActionState,
  buildCustomerAssistantState,
  formatCustomerAssistantEvents,
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
