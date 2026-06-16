import { describe, expect, it } from 'vitest'

import {
  mockCustomerAssistantEvents,
  mockCustomerAssistantTasks,
  mockCustomerAssistantTurnResult,
} from './customerAssistantFixtures'

describe('customer-assistant fixture contract', () => {
  it('matches 045 turn result fields used by the operator panel', () => {
    expect(mockCustomerAssistantTurnResult).toMatchObject({
      runId: expect.any(Number),
      sessionId: expect.any(Number),
      replyType: 'DRAFT',
      operatorRecommendation: expect.any(String),
      customerReplyDraft: expect.any(String),
      replayed: false,
    })
    expect(mockCustomerAssistantTurnResult.taskSummaries[0]).toMatchObject({
      taskKey: 'refund_ticket',
      status: expect.any(String),
      workerType: expect.any(String),
      checkpoint: expect.any(Object),
    })
    expect(mockCustomerAssistantTurnResult.proposedActions[0]).toMatchObject({
      id: expect.any(Number),
      actionType: 'submit_refund',
      title: expect.any(String),
      status: 'PENDING',
      payload: expect.any(Object),
    })
  })

  it('matches 045 task and event ledger envelopes', () => {
    expect(mockCustomerAssistantTasks).toMatchObject({
      list: expect.any(Array),
      total: expect.any(Number),
    })
    expect(mockCustomerAssistantTasks.list[0]).toMatchObject({
      id: expect.any(Number),
      sessionId: expect.any(Number),
      taskKey: expect.any(String),
      status: expect.any(String),
      proposedActions: expect.any(Array),
    })
    expect(mockCustomerAssistantEvents).toMatchObject({
      list: expect.any(Array),
      total: expect.any(Number),
    })
    expect(mockCustomerAssistantEvents.list[0]).toMatchObject({
      id: expect.any(Number),
      sessionId: expect.any(Number),
      sequence: expect.any(Number),
      type: expect.any(String),
      payload: expect.any(Object),
    })
  })
})
