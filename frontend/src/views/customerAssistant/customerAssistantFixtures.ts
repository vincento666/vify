import type {
  CustomerAssistantEvent,
  CustomerAssistantListResult,
  CustomerAssistantSessionMetrics,
  CustomerAssistantTask,
  CustomerAssistantTurnResult,
} from '@/api/customerAssistant'

export const mockCustomerAssistantTurnResult: CustomerAssistantTurnResult = {
  runId: 31,
  sessionId: 12,
  replyType: 'DRAFT',
  operatorRecommendation: 'Operator recommendations:\n- refund_ticket worker WAITING at collect_order_no',
  customerReplyDraft: '为了帮您继续办理退票，请补充订单号。',
  taskSummaries: [
    {
      id: 101,
      sessionId: 12,
      taskKey: 'refund_ticket',
      taskType: 'refund',
      businessKey: 'refund_ticket',
      shortId: 'refund-101',
      status: 'WAITING',
      workerType: 'chatflow_sop',
      workerRef: 'flight_refund',
      checkpoint: {
        currentStep: 'collect_order_no',
        pendingPrompt: '请提供订单号',
        collected: {},
      },
      lastResult: {
        missingFields: ['订单号'],
        operatorRecommendation: '继续收集退票订单号。',
      },
      proposedActions: [],
      version: 1,
    },
  ],
  proposedActions: [
    {
      id: 9,
      sessionId: 12,
      runId: 31,
      taskId: 101,
      actionKey: 'refund_ticket:submit_refund:TK-100',
      actionType: 'submit_refund',
      title: '提交退票申请',
      payload: { orderNo: 'TK-100' },
      status: 'PENDING',
    },
  ],
  warnings: ['缺少订单号时不可提交退票动作。'],
  events: [
    {
      id: 501,
      sessionId: 12,
      runId: 31,
      sequence: 1,
      type: 'run_started',
      visibility: 'normal',
      source: 'customer_assistant',
      actor: 'customer',
      taskId: null,
      parentSpanId: null,
      spanId: 'run-31',
      payload: { message: '我要退票' },
      createdAt: '2026-06-14T04:00:00',
    },
  ],
  replayed: false,
}

export const mockCustomerAssistantTasks: CustomerAssistantListResult<CustomerAssistantTask> = {
  list: mockCustomerAssistantTurnResult.taskSummaries,
  total: mockCustomerAssistantTurnResult.taskSummaries.length,
}

export const mockCustomerAssistantEvents: CustomerAssistantListResult<CustomerAssistantEvent> = {
  list: mockCustomerAssistantTurnResult.events,
  total: mockCustomerAssistantTurnResult.events.length,
}

export const mockCustomerAssistantMetrics: CustomerAssistantSessionMetrics = {
  sessionId: 12,
  taskStatusCounts: { WAITING: 1 },
  proposedActionStatusCounts: { PENDING: 1 },
  humanConfirmation: {
    pending: 1,
    adopted: 0,
    terminal: 0,
    adoptionRate: 0,
  },
  eventCounts: {
    total: 1,
    byType: { run_started: 1 },
    bySource: { customer_assistant: 1 },
  },
  workerEventCounts: {
    total: 0,
    byType: {},
  },
  recentFailureReasons: [],
}
