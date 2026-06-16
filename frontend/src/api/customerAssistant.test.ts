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

  it('lists seeded demo stories', async () => {
    requestMocks.get.mockResolvedValueOnce({ list: [{ storyId: 'refund_baggage_parallel' }], total: 1 })

    const { listCustomerAssistantDemoStories } = await import('./customerAssistant')

    await expect(listCustomerAssistantDemoStories()).resolves.toEqual({
      list: [{ storyId: 'refund_baggage_parallel' }],
      total: 1,
    })
    expect(requestMocks.get).toHaveBeenCalledWith('/v1/customer-assistant/demo-stories')
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
})
