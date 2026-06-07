import { describe, expect, it } from 'vitest'

import {
  AIRLINE_SOP_SCENARIOS,
  buildRuntimeLabTranscriptRow,
  getAirlineSopScenario,
} from './unifiedRoutingChatLab'

describe('unified routing chat lab model', () => {
  it('offers the ten airline SOP scenarios used by the runtime business gate', () => {
    expect(AIRLINE_SOP_SCENARIOS.map((scenario) => scenario.id)).toEqual([
      'refund_ticket',
      'change_flight',
      'invoice_apply',
      'baggage_service',
      'seat_checkin',
      'flight_status',
      'special_assistance',
      'pet_cabin',
      'irregular_flight',
      'membership_service',
    ])
    expect(getAirlineSopScenario('refund_ticket')?.startMessage).toContain('退票')
    expect(getAirlineSopScenario('seat_checkin')?.startMessage).toContain('选座')
    expect(getAirlineSopScenario('flight_status')?.startMessage).toContain('航班动态')
    expect(getAirlineSopScenario('membership_service')?.startMessage).toContain('会员')
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
})
