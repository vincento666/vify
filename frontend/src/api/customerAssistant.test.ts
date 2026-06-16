import { beforeEach, describe, expect, it, vi } from 'vitest'

const requestMocks = vi.hoisted(() => ({
  get: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
}))

vi.mock('@/utils/request', () => requestMocks)

describe('customer-assistant frontend API client', () => {
  beforeEach(() => {
    requestMocks.get.mockReset()
    requestMocks.patch.mockReset()
    requestMocks.post.mockReset()
  })

  it('uses the customer-assistant session and turn endpoints', async () => {
    requestMocks.post
      .mockResolvedValueOnce({ id: 12, status: 'ACTIVE' })
      .mockResolvedValueOnce({ runId: 31, customerReplyDraft: '请补充订单号。' })

    const { createCustomerAssistantSession, sendCustomerAssistantTurn } = await import('./customerAssistant')

    await expect(createCustomerAssistantSession({ customerId: 'C-046' })).resolves.toEqual({
      id: 12,
      status: 'ACTIVE',
    })
    await expect(
      sendCustomerAssistantTurn(12, {
        message: '我要退票',
        idempotencyKey: '046-red',
      }),
    ).resolves.toEqual({ runId: 31, customerReplyDraft: '请补充订单号。' })

    expect(requestMocks.post).toHaveBeenNthCalledWith(1, '/v1/customer-assistant/sessions', {
      context: { customerId: 'C-046' },
    })
    expect(requestMocks.post).toHaveBeenNthCalledWith(2, '/v1/customer-assistant/sessions/12/turns', {
      message: '我要退票',
      idempotencyKey: '046-red',
    })
  })

  it('sends actor through the turn endpoint', async () => {
    requestMocks.post.mockResolvedValueOnce({ runId: 47 })

    const { sendCustomerAssistantTurn } = await import('./customerAssistant')

    await sendCustomerAssistantTurn(12, {
      message: '请帮我看下退票建议',
      idempotencyKey: '047-actor',
      actor: 'operator',
    })

    expect(requestMocks.post).toHaveBeenCalledWith('/v1/customer-assistant/sessions/12/turns', {
      message: '请帮我看下退票建议',
      idempotencyKey: '047-actor',
      actor: 'operator',
    })
  })

  it('lists task and event ledgers', async () => {
    requestMocks.get
      .mockResolvedValueOnce({ list: [], total: 0 })
      .mockResolvedValueOnce({ list: [], total: 0 })
      .mockResolvedValueOnce({ list: [], total: 0 })

    const { listCustomerAssistantEvents, listCustomerAssistantProposedActions, listCustomerAssistantTasks } =
      await import('./customerAssistant')

    await listCustomerAssistantTasks(7)
    await listCustomerAssistantEvents(7)
    await listCustomerAssistantProposedActions(7)

    expect(requestMocks.get).toHaveBeenNthCalledWith(1, '/v1/customer-assistant/sessions/7/tasks')
    expect(requestMocks.get).toHaveBeenNthCalledWith(2, '/v1/customer-assistant/sessions/7/events')
    expect(requestMocks.get).toHaveBeenNthCalledWith(3, '/v1/customer-assistant/sessions/7/proposed-actions')
  })

  it('loads session observability metrics', async () => {
    requestMocks.get.mockResolvedValueOnce({
      sessionId: 7,
      taskStatusCounts: { FAILED: 1 },
      proposedActionStatusCounts: { PENDING: 1 },
      humanConfirmation: { pending: 1, adopted: 0, terminal: 0, adoptionRate: 0 },
      eventCounts: { total: 2, byType: { task_failed: 1 }, bySource: { chatflow_sop: 1 } },
      workerEventCounts: { total: 1, byType: { task_failed: 1 } },
      recentFailureReasons: [{ taskId: 101, taskType: 'REFUND', source: 'chatflow_sop', reason: '[REDACTED]' }],
    })

    const { getCustomerAssistantSessionMetrics } = await import('./customerAssistant')

    await expect(getCustomerAssistantSessionMetrics(7)).resolves.toMatchObject({
      sessionId: 7,
      humanConfirmation: { pending: 1, adoptionRate: 0 },
    })
    expect(requestMocks.get).toHaveBeenCalledWith('/v1/customer-assistant/sessions/7/metrics')
  })

  it('lists session-scoped operator audit rows', async () => {
    requestMocks.get.mockResolvedValueOnce({
      sessionId: 7,
      list: [{ eventType: 'proposed_action_confirmed', summary: 'submit_refund CONFIRMED' }],
      total: 1,
    })

    const { listCustomerAssistantOperatorAudit } = await import('./customerAssistant')

    await expect(listCustomerAssistantOperatorAudit(7)).resolves.toMatchObject({
      total: 1,
      list: [{ eventType: 'proposed_action_confirmed' }],
    })
    expect(requestMocks.get).toHaveBeenCalledWith('/v1/customer-assistant/sessions/7/operator-audit')
  })

  it('lists seeded demo stories', async () => {
    requestMocks.get.mockResolvedValueOnce({ list: [{ storyId: 'refund_baggage_parallel' }], total: 1 })

    const { listCustomerAssistantDemoStories } = await import('./customerAssistant')

    await expect(listCustomerAssistantDemoStories()).resolves.toEqual({
      list: [{ storyId: 'refund_baggage_parallel' }],
      total: 1,
    })
    expect(requestMocks.get).toHaveBeenCalledWith('/v1/customer-assistant/demo-stories')
  })

  it('loads seeded demo story observability metrics', async () => {
    requestMocks.get.mockResolvedValueOnce({
      storyCount: 3,
      sessionCount: 3,
      taskStatusCounts: { WAITING: 1, COMPLETED: 2 },
      proposedActionStatusCounts: { PENDING: 3 },
      humanConfirmation: { pending: 3, adopted: 0, terminal: 0, adoptionRate: 0 },
      eventCounts: { total: 12, byType: { task_created: 3 }, bySource: { demo_seed: 3 } },
      workerEventCounts: { total: 4, byType: { worker_started: 2 } },
      recentFailureReasons: [],
      stories: [{ storyId: 'refund_baggage_parallel', title: '退票 + 行李额', sessionId: 7 }],
    })

    const { getCustomerAssistantDemoStoryMetrics } = await import('./customerAssistant')

    await expect(getCustomerAssistantDemoStoryMetrics()).resolves.toMatchObject({
      storyCount: 3,
      humanConfirmation: { pending: 3 },
    })
    expect(requestMocks.get).toHaveBeenCalledWith('/v1/customer-assistant/demo-stories/metrics')
  })

  it('lists worker profile catalog entries for the workbench', async () => {
    requestMocks.get.mockResolvedValueOnce({
      list: [{ profileId: 'refund_ticket_chatflow', taskKey: 'refund_ticket' }],
      total: 1,
    })

    const { listCustomerAssistantWorkerProfiles } = await import('./customerAssistant')

    await expect(listCustomerAssistantWorkerProfiles()).resolves.toEqual({
      list: [{ profileId: 'refund_ticket_chatflow', taskKey: 'refund_ticket' }],
      total: 1,
    })
    expect(requestMocks.get).toHaveBeenCalledWith('/v1/customer-assistant/worker-profiles')
  })

  it('updates worker profile catalog entries through the patch endpoint', async () => {
    requestMocks.patch.mockResolvedValueOnce({
      profileId: 'refund_ticket_chatflow',
      taskKey: 'refund_ticket',
      workerRef: 'runtime_configured_refund',
    })

    const { updateCustomerAssistantWorkerProfile } = await import('./customerAssistant')

    await expect(
      updateCustomerAssistantWorkerProfile('refund_ticket_chatflow', {
        taskKey: 'refund_ticket',
        taskType: 'REFUND',
        workerType: 'chatflow_sop',
        workerRef: 'runtime_configured_refund',
        modelPolicyRef: 'demo-model-v2',
        promptRef: 'runtime-refund-prompt',
        toolRefs: ['lookup_order', 'refund_policy_lookup'],
        riskPolicyRef: 'manual_confirm_high_risk',
        enabled: true,
      }),
    ).resolves.toMatchObject({ workerRef: 'runtime_configured_refund' })
    expect(requestMocks.patch).toHaveBeenCalledWith(
      '/v1/customer-assistant/worker-profiles/refund_ticket_chatflow',
      {
        taskKey: 'refund_ticket',
        taskType: 'REFUND',
        workerType: 'chatflow_sop',
        workerRef: 'runtime_configured_refund',
        modelPolicyRef: 'demo-model-v2',
        promptRef: 'runtime-refund-prompt',
        toolRefs: ['lookup_order', 'refund_policy_lookup'],
        riskPolicyRef: 'manual_confirm_high_risk',
        enabled: true,
      },
    )
  })

  it('confirms, rejects, and executes proposed actions through explicit endpoints', async () => {
    requestMocks.post
      .mockResolvedValueOnce({ id: 9, status: 'CONFIRMED' })
      .mockResolvedValueOnce({ id: 10, status: 'REJECTED' })
      .mockResolvedValueOnce({ id: 11, status: 'EXECUTED' })

    const { confirmCustomerAssistantAction, executeCustomerAssistantAction, rejectCustomerAssistantAction } =
      await import('./customerAssistant')

    await expect(confirmCustomerAssistantAction(9)).resolves.toEqual({ id: 9, status: 'CONFIRMED' })
    await expect(rejectCustomerAssistantAction(10)).resolves.toEqual({ id: 10, status: 'REJECTED' })
    await expect(executeCustomerAssistantAction(11)).resolves.toEqual({ id: 11, status: 'EXECUTED' })

    expect(requestMocks.post).toHaveBeenNthCalledWith(1, '/v1/customer-assistant/proposed-actions/9/confirm')
    expect(requestMocks.post).toHaveBeenNthCalledWith(2, '/v1/customer-assistant/proposed-actions/10/reject')
    expect(requestMocks.post).toHaveBeenNthCalledWith(3, '/v1/customer-assistant/proposed-actions/11/execute')
  })

  it('updates pending proposed actions through the patch endpoint', async () => {
    requestMocks.patch.mockResolvedValueOnce({ id: 9, title: '提交退票申请（已修正）', status: 'PENDING' })

    const { updateCustomerAssistantAction } = await import('./customerAssistant')

    await expect(
      updateCustomerAssistantAction(9, {
        title: '提交退票申请（已修正）',
        payload: { orderNo: 'TK-100', amount: 300 },
      }),
    ).resolves.toEqual({ id: 9, title: '提交退票申请（已修正）', status: 'PENDING' })
    expect(requestMocks.patch).toHaveBeenCalledWith('/v1/customer-assistant/proposed-actions/9', {
      title: '提交退票申请（已修正）',
      payload: { orderNo: 'TK-100', amount: 300 },
    })
  })

  it('proposes task controls through the session task endpoint', async () => {
    requestMocks.post.mockResolvedValueOnce({ id: 42, status: 'PENDING' })

    const { proposeCustomerAssistantTaskControl } = await import('./customerAssistant')

    await expect(
      proposeCustomerAssistantTaskControl(12, 101, {
        controlType: 'resume',
        reason: 'customer supplied missing order number',
      }),
    ).resolves.toEqual({ id: 42, status: 'PENDING' })

    expect(requestMocks.post).toHaveBeenCalledWith('/v1/customer-assistant/sessions/12/tasks/101/controls/propose', {
      controlType: 'resume',
      reason: 'customer supplied missing order number',
    })
  })

  it('refreshes pending worker results through the session endpoint', async () => {
    requestMocks.post.mockResolvedValueOnce({ consumed: 1 })

    const { refreshCustomerAssistantWorkerResults } = await import('./customerAssistant')

    await expect(refreshCustomerAssistantWorkerResults(12)).resolves.toEqual({ consumed: 1 })
    expect(requestMocks.post).toHaveBeenCalledWith('/v1/customer-assistant/sessions/12/worker-results/refresh')
  })
})
