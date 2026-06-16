import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  mockCustomerAssistantEvents,
  mockCustomerAssistantMetrics,
  mockCustomerAssistantOperatorAudit,
  mockCustomerAssistantTasks,
  mockCustomerAssistantTurnResult,
} from './customerAssistantFixtures'

const apiMocks = vi.hoisted(() => ({
  confirmCustomerAssistantAction: vi.fn(),
  createCustomerAssistantSession: vi.fn(),
  executeCustomerAssistantAction: vi.fn(),
  getCustomerAssistantSessionMetrics: vi.fn(),
  listCustomerAssistantDemoStories: vi.fn(),
  listCustomerAssistantEvents: vi.fn(),
  listCustomerAssistantOperatorAudit: vi.fn(),
  listCustomerAssistantProposedActions: vi.fn(),
  listCustomerAssistantTasks: vi.fn(),
  proposeCustomerAssistantTaskControl: vi.fn(),
  rejectCustomerAssistantAction: vi.fn(),
  refreshCustomerAssistantWorkerResults: vi.fn(),
  sendCustomerAssistantTurn: vi.fn(),
  updateCustomerAssistantAction: vi.fn(),
}))

vi.mock('@/api/customerAssistant', () => apiMocks)

const streamMocks = vi.hoisted(() => ({
  openCustomerAssistantEventStream: vi.fn(),
}))

vi.mock('./customerAssistantEventStream', () => streamMocks)

describe('customer assistant runtime integration', () => {
  beforeEach(() => {
    Object.values(apiMocks).forEach((mock) => mock.mockReset())
    apiMocks.getCustomerAssistantSessionMetrics.mockResolvedValue(mockCustomerAssistantMetrics)
    apiMocks.listCustomerAssistantOperatorAudit.mockResolvedValue(mockCustomerAssistantOperatorAudit)
    streamMocks.openCustomerAssistantEventStream.mockReset()
  })

  it('creates a session before the first turn and refreshes task/event ledgers after the turn', async () => {
    apiMocks.createCustomerAssistantSession.mockResolvedValue({ id: 12, status: 'ACTIVE' })
    apiMocks.sendCustomerAssistantTurn.mockResolvedValue(mockCustomerAssistantTurnResult)
    apiMocks.listCustomerAssistantTasks.mockResolvedValue(mockCustomerAssistantTasks)
    apiMocks.listCustomerAssistantEvents.mockResolvedValue(mockCustomerAssistantEvents)
    apiMocks.listCustomerAssistantProposedActions.mockResolvedValue({
      list: mockCustomerAssistantTurnResult.proposedActions,
      total: 1,
    })

    const { createCustomerAssistantRuntimeState, sendCustomerAssistantRuntimeTurn } = await import(
      './customerAssistantRuntime'
    )

    const state = await sendCustomerAssistantRuntimeTurn(createCustomerAssistantRuntimeState(), {
      message: '我要退票',
      idempotencyKey: '046-real-api',
      actor: 'customer',
    })

    expect(apiMocks.createCustomerAssistantSession).toHaveBeenCalledWith({})
    expect(apiMocks.sendCustomerAssistantTurn).toHaveBeenCalledWith(12, {
      message: '我要退票',
      idempotencyKey: '046-real-api',
      actor: 'customer',
    })
    expect(apiMocks.listCustomerAssistantTasks).toHaveBeenCalledWith(12)
    expect(apiMocks.listCustomerAssistantEvents).toHaveBeenCalledWith(12)
    expect(apiMocks.listCustomerAssistantProposedActions).toHaveBeenCalledWith(12)
    expect(apiMocks.getCustomerAssistantSessionMetrics).toHaveBeenCalledWith(12)
    expect(apiMocks.listCustomerAssistantOperatorAudit).toHaveBeenCalledWith(12)
    expect(state.session?.id).toBe(12)
    expect(state.metrics?.humanConfirmation.pending).toBe(1)
    expect(state.operatorAudit.list[0].eventType).toBe('proposed_action_confirmed')
    expect(state.taskSummary.items[0].taskKey).toBe('refund_ticket')
    expect(state.eventTimeline[0].title).toBe('run_started')
  })

  it('reuses an existing session for later turns', async () => {
    apiMocks.sendCustomerAssistantTurn.mockResolvedValue(mockCustomerAssistantTurnResult)
    apiMocks.listCustomerAssistantTasks.mockResolvedValue(mockCustomerAssistantTasks)
    apiMocks.listCustomerAssistantEvents.mockResolvedValue(mockCustomerAssistantEvents)
    apiMocks.listCustomerAssistantProposedActions.mockResolvedValue({
      list: mockCustomerAssistantTurnResult.proposedActions,
      total: 1,
    })

    const { createCustomerAssistantRuntimeState, sendCustomerAssistantRuntimeTurn } = await import(
      './customerAssistantRuntime'
    )

    await sendCustomerAssistantRuntimeTurn(
      createCustomerAssistantRuntimeState({ session: { id: 12, status: 'ACTIVE' } }),
      {
        message: '请给我处置建议',
        actor: 'operator',
      },
    )

    expect(apiMocks.createCustomerAssistantSession).not.toHaveBeenCalled()
    expect(apiMocks.sendCustomerAssistantTurn).toHaveBeenCalledWith(12, {
      message: '请给我处置建议',
      actor: 'operator',
    })
  })

  it('opens SSE before a turn and publishes live state while the turn request is pending', async () => {
    apiMocks.createCustomerAssistantSession.mockResolvedValue({ id: 12, status: 'ACTIVE' })
    apiMocks.listCustomerAssistantTasks.mockResolvedValue(mockCustomerAssistantTasks)
    apiMocks.listCustomerAssistantEvents.mockResolvedValue(mockCustomerAssistantEvents)
    apiMocks.listCustomerAssistantProposedActions.mockResolvedValue({
      list: mockCustomerAssistantTurnResult.proposedActions,
      total: 1,
    })
    let resolveTurn: (value: typeof mockCustomerAssistantTurnResult) => void = () => {}
    apiMocks.sendCustomerAssistantTurn.mockReturnValue(
      new Promise((resolve) => {
        resolveTurn = resolve
      }),
    )
    let emitLiveEvent: (event: never) => void = () => {}
    const close = vi.fn()
    streamMocks.openCustomerAssistantEventStream.mockImplementation((_sessionId, options) => {
      emitLiveEvent = options.onEvent
      return { close, lastSequence: () => 2 }
    })
    const liveStates: ReturnType<typeof createCustomerAssistantRuntimeState>[] = []

    const { createCustomerAssistantRuntimeState, sendCustomerAssistantRuntimeTurn } = await import(
      './customerAssistantRuntime'
    )

    const pending = sendCustomerAssistantRuntimeTurn(
      createCustomerAssistantRuntimeState(),
      { message: '我要退票', actor: 'customer' },
      {},
      { onLiveState: (state) => liveStates.push(state) },
    )
    await Promise.resolve()
    emitLiveEvent({
      id: 502,
      sessionId: 12,
      sequence: 2,
      type: 'worker_started',
      source: 'chatflow_sop',
      payload: { taskKey: 'refund_ticket', workerType: 'chatflow_sop' },
    } as never)

    expect(streamMocks.openCustomerAssistantEventStream).toHaveBeenCalledWith(12, expect.any(Object))
    const latestLiveState = liveStates[liveStates.length - 1]
    expect(latestLiveState.eventTimeline[0]).toMatchObject({ title: 'worker_started' })
    expect(latestLiveState.taskSummary.items[0]).toMatchObject({
      taskKey: 'refund_ticket',
      status: 'RUNNING',
    })

    resolveTurn(mockCustomerAssistantTurnResult)
    const finalState = await pending

    expect(close).toHaveBeenCalled()
    expect(finalState.taskSummary.items[0].status).toBe('WAITING')
  })

  it('refreshes ledgers after confirming and rejecting proposed actions', async () => {
    const pending = mockCustomerAssistantTurnResult.proposedActions[0]
    apiMocks.confirmCustomerAssistantAction.mockResolvedValue({ ...pending, status: 'CONFIRMED' })
    apiMocks.rejectCustomerAssistantAction.mockResolvedValue({ ...pending, status: 'REJECTED' })
    apiMocks.listCustomerAssistantTasks
      .mockResolvedValueOnce(mockCustomerAssistantTasks)
      .mockResolvedValueOnce(mockCustomerAssistantTasks)
    apiMocks.listCustomerAssistantEvents
      .mockResolvedValueOnce({
        list: [
          ...mockCustomerAssistantEvents.list,
          {
            id: 779,
            sessionId: 12,
            sequence: 2,
            type: 'proposed_action_confirmed',
            source: 'operator_advisory',
            payload: { actionId: pending.id },
          },
        ],
        total: 2,
      })
      .mockResolvedValueOnce({
        list: [
          ...mockCustomerAssistantEvents.list,
          {
            id: 780,
            sessionId: 12,
            sequence: 2,
            type: 'proposed_action_rejected',
            source: 'operator_advisory',
            payload: { actionId: pending.id },
          },
        ],
        total: 2,
      })
    apiMocks.listCustomerAssistantProposedActions
      .mockResolvedValueOnce({ list: [{ ...pending, status: 'CONFIRMED' }], total: 1 })
      .mockResolvedValueOnce({ list: [{ ...pending, status: 'REJECTED' }], total: 1 })

    const {
      confirmCustomerAssistantRuntimeAction,
      createCustomerAssistantRuntimeState,
      rejectCustomerAssistantRuntimeAction,
    } = await import('./customerAssistantRuntime')
    const initial = createCustomerAssistantRuntimeState({
      session: { id: 12, status: 'ACTIVE' },
      turnResult: mockCustomerAssistantTurnResult,
    })

    const confirmed = await confirmCustomerAssistantRuntimeAction(initial, pending.id)
    const rejected = await rejectCustomerAssistantRuntimeAction(initial, pending.id)

    expect(apiMocks.confirmCustomerAssistantAction).toHaveBeenCalledWith(pending.id)
    expect(apiMocks.rejectCustomerAssistantAction).toHaveBeenCalledWith(pending.id)
    expect(apiMocks.listCustomerAssistantTasks).toHaveBeenCalledWith(12)
    expect(apiMocks.listCustomerAssistantEvents).toHaveBeenCalledWith(12)
    expect(apiMocks.listCustomerAssistantProposedActions).toHaveBeenCalledWith(12)
    expect(confirmed.proposedActions[0].status).toBe('CONFIRMED')
    expect(rejected.proposedActions[0].status).toBe('REJECTED')
    expect(confirmed.eventTimeline.some((event) => event.title === 'proposed_action_confirmed')).toBe(true)
    expect(rejected.eventTimeline.some((event) => event.title === 'proposed_action_rejected')).toBe(true)
  })

  it('refreshes ledgers after editing a pending proposed action', async () => {
    const pending = mockCustomerAssistantTurnResult.proposedActions[0]
    const editedAction = {
      ...pending,
      title: '提交退票申请（已修正）',
      payload: { ...pending.payload, amount: 300 },
    }
    apiMocks.updateCustomerAssistantAction.mockResolvedValue({
      ...editedAction,
      title: '提交退票申请（本地返回）',
    })
    apiMocks.listCustomerAssistantTasks.mockResolvedValue(mockCustomerAssistantTasks)
    apiMocks.listCustomerAssistantEvents.mockResolvedValue({
      list: [
        ...mockCustomerAssistantEvents.list,
        {
          id: 781,
          sessionId: 12,
          sequence: 2,
          type: 'proposed_action_modified',
          source: 'operator_advisory',
          payload: { actionId: pending.id, changedFields: ['title', 'payload'] },
        },
      ],
      total: 2,
    })
    apiMocks.listCustomerAssistantProposedActions.mockResolvedValue({ list: [editedAction], total: 1 })

    const { createCustomerAssistantRuntimeState, updateCustomerAssistantRuntimeAction } = await import(
      './customerAssistantRuntime'
    )
    const initial = createCustomerAssistantRuntimeState({
      session: { id: 12, status: 'ACTIVE' },
      turnResult: mockCustomerAssistantTurnResult,
    })

    const updated = await updateCustomerAssistantRuntimeAction(initial, pending.id, {
      title: '提交退票申请（已修正）',
      payload: { ...pending.payload, amount: 300 },
    })

    expect(apiMocks.updateCustomerAssistantAction).toHaveBeenCalledWith(pending.id, {
      title: '提交退票申请（已修正）',
      payload: { ...pending.payload, amount: 300 },
    })
    expect(apiMocks.listCustomerAssistantTasks).toHaveBeenCalledWith(12)
    expect(apiMocks.listCustomerAssistantEvents).toHaveBeenCalledWith(12)
    expect(apiMocks.listCustomerAssistantProposedActions).toHaveBeenCalledWith(12)
    expect(updated.proposedActions[0]).toMatchObject({
      id: pending.id,
      title: '提交退票申请（已修正）',
      payload: { ...pending.payload, amount: 300 },
    })
    expect(updated.eventTimeline.some((event) => event.title === 'proposed_action_modified')).toBe(true)
  })

  it('refreshes ledgers after executing a confirmed proposed action', async () => {
    const pending = mockCustomerAssistantTurnResult.proposedActions[0]
    const confirmed = { ...pending, status: 'CONFIRMED' }
    const executedAction = {
      ...confirmed,
      status: 'EXECUTED',
      result: { audit: { semanticCode: 'REFUND_SUBMITTED_MOCK' } },
    }
    apiMocks.executeCustomerAssistantAction.mockResolvedValue({
      ...executedAction,
      title: '提交退票申请（本地执行回执）',
    })
    apiMocks.listCustomerAssistantTasks.mockResolvedValue({
      list: [{ ...mockCustomerAssistantTasks.list[0], status: 'COMPLETED' }],
      total: 1,
    })
    apiMocks.listCustomerAssistantEvents.mockResolvedValue({
      list: [
        ...mockCustomerAssistantEvents.list,
        {
          id: 782,
          sessionId: 12,
          sequence: 2,
          type: 'proposed_action_executed',
          source: 'operator_advisory',
          payload: { actionId: pending.id, status: 'EXECUTED' },
        },
      ],
      total: 2,
    })
    apiMocks.listCustomerAssistantProposedActions.mockResolvedValue({ list: [executedAction], total: 1 })

    const { createCustomerAssistantRuntimeState, executeCustomerAssistantRuntimeAction } = await import(
      './customerAssistantRuntime'
    )
    const initial = createCustomerAssistantRuntimeState({
      session: { id: 12, status: 'ACTIVE' },
      turnResult: {
        ...mockCustomerAssistantTurnResult,
        proposedActions: [confirmed],
      },
    })

    const executed = await executeCustomerAssistantRuntimeAction(initial, pending.id)

    expect(apiMocks.executeCustomerAssistantAction).toHaveBeenCalledWith(pending.id)
    expect(apiMocks.listCustomerAssistantTasks).toHaveBeenCalledWith(12)
    expect(apiMocks.listCustomerAssistantEvents).toHaveBeenCalledWith(12)
    expect(apiMocks.listCustomerAssistantProposedActions).toHaveBeenCalledWith(12)
    expect(executed.proposedActions[0]).toMatchObject({
      id: pending.id,
      title: '提交退票申请',
      status: 'EXECUTED',
    })
    expect(executed.taskSummary.items[0].status).toBe('COMPLETED')
    expect(executed.eventTimeline.some((event) => event.title === 'proposed_action_executed')).toBe(true)
  })

  it('refreshes ledgers after confirming a proposed task command', async () => {
    const proposedTaskCommand = {
      ...mockCustomerAssistantTurnResult.proposedActions[0],
      taskId: null,
      actionType: 'PROPOSED_TASK_COMMAND',
      title: '确认任务变更：refund_ticket',
      payload: {
        taskCommand: {
          type: 'ADD_TASK',
          taskKey: 'refund_ticket',
          taskType: 'REFUND',
          businessKey: 'refund_ticket',
          workerType: 'chatflow_sop',
          workerRef: 'refund_ticket',
        },
      },
      status: 'PENDING',
    }
    apiMocks.confirmCustomerAssistantAction.mockResolvedValue({ ...proposedTaskCommand, status: 'CONFIRMED' })
    apiMocks.listCustomerAssistantTasks.mockResolvedValue(mockCustomerAssistantTasks)
    apiMocks.listCustomerAssistantEvents.mockResolvedValue({
      list: [
        ...mockCustomerAssistantEvents.list,
        {
          id: 777,
          sessionId: 12,
          runId: 31,
          sequence: 2,
          type: 'proposed_task_command_confirmed',
          source: 'operator_advisory',
          payload: { actionId: proposedTaskCommand.id },
        },
      ],
      total: 2,
    })
    apiMocks.listCustomerAssistantProposedActions.mockResolvedValue({
      list: [{ ...proposedTaskCommand, status: 'CONFIRMED' }],
      total: 1,
    })

    const { confirmCustomerAssistantRuntimeAction, createCustomerAssistantRuntimeState } = await import(
      './customerAssistantRuntime'
    )
    const initial = createCustomerAssistantRuntimeState({
      session: { id: 12, status: 'ACTIVE' },
      turnResult: {
        ...mockCustomerAssistantTurnResult,
        taskSummaries: [],
        proposedActions: [proposedTaskCommand],
      },
    })

    const confirmed = await confirmCustomerAssistantRuntimeAction(initial, proposedTaskCommand.id)

    expect(apiMocks.listCustomerAssistantTasks).toHaveBeenCalledWith(12)
    expect(apiMocks.listCustomerAssistantEvents).toHaveBeenCalledWith(12)
    expect(apiMocks.getCustomerAssistantSessionMetrics).toHaveBeenCalledWith(12)
    expect(confirmed.proposedActions[0].status).toBe('CONFIRMED')
    expect(confirmed.metrics?.eventCounts.total).toBe(mockCustomerAssistantMetrics.eventCounts.total)
    expect(confirmed.taskSummary.items[0].taskKey).toBe('refund_ticket')
    expect(confirmed.eventTimeline.some((event) => event.title === 'proposed_task_command_confirmed')).toBe(true)
  })

  it('refreshes pending worker results and reloads runtime ledgers', async () => {
    apiMocks.refreshCustomerAssistantWorkerResults.mockResolvedValue({ consumed: 1 })
    apiMocks.listCustomerAssistantTasks.mockResolvedValue({
      list: [{ ...mockCustomerAssistantTasks.list[0], status: 'COMPLETED' }],
      total: 1,
    })
    apiMocks.listCustomerAssistantEvents.mockResolvedValue(mockCustomerAssistantEvents)
    apiMocks.listCustomerAssistantProposedActions.mockResolvedValue({
      list: mockCustomerAssistantTurnResult.proposedActions,
      total: 1,
    })

    const { createCustomerAssistantRuntimeState, refreshCustomerAssistantRuntimeWorkerResults } = await import(
      './customerAssistantRuntime'
    )
    const initial = createCustomerAssistantRuntimeState({
      session: { id: 12, status: 'ACTIVE' },
      turnResult: mockCustomerAssistantTurnResult,
    })

    const refreshed = await refreshCustomerAssistantRuntimeWorkerResults(initial)

    expect(apiMocks.refreshCustomerAssistantWorkerResults).toHaveBeenCalledWith(12)
    expect(apiMocks.listCustomerAssistantTasks).toHaveBeenCalledWith(12)
    expect(refreshed.taskSummary.items[0].status).toBe('COMPLETED')
  })

  it('loads a seeded demo story into the workbench state', async () => {
    apiMocks.listCustomerAssistantDemoStories.mockResolvedValue({
      list: [
        {
          storyId: 'refund_baggage_parallel',
          title: '退票 + 行李额并行',
          sessionId: 73,
          customerName: '赵女士',
          taskCount: 2,
          pendingActionCount: 1,
          knowledgeBaseIds: [201],
        },
      ],
      total: 1,
    })
    apiMocks.listCustomerAssistantTasks.mockResolvedValue(mockCustomerAssistantTasks)
    apiMocks.listCustomerAssistantEvents.mockResolvedValue(mockCustomerAssistantEvents)
    apiMocks.listCustomerAssistantProposedActions.mockResolvedValue({
      list: mockCustomerAssistantTurnResult.proposedActions,
      total: 1,
    })

    const { loadCustomerAssistantDemoStory } = await import('./customerAssistantRuntime')

    const state = await loadCustomerAssistantDemoStory('refund_baggage_parallel')

    expect(apiMocks.listCustomerAssistantDemoStories).toHaveBeenCalled()
    expect(apiMocks.listCustomerAssistantTasks).toHaveBeenCalledWith(73)
    expect(apiMocks.listCustomerAssistantEvents).toHaveBeenCalledWith(73)
    expect(apiMocks.listCustomerAssistantProposedActions).toHaveBeenCalledWith(73)
    expect(apiMocks.getCustomerAssistantSessionMetrics).toHaveBeenCalledWith(73)
    expect(state.session?.id).toBe(73)
    expect(state.metrics?.taskStatusCounts.WAITING).toBe(1)
    expect(state.taskSummary.items[0].taskKey).toBe('refund_ticket')
    expect(state.proposedActions[0].title).toBe(mockCustomerAssistantTurnResult.proposedActions[0].title)
    expect(state.eventTimeline[0].title).toBe('run_started')
  })

  it('proposes a task control and refreshes ledgers', async () => {
    const proposedControl = {
      ...mockCustomerAssistantTurnResult.proposedActions[0],
      id: 88,
      actionType: 'PROPOSED_TASK_COMMAND',
      title: '恢复任务：refund_ticket',
      payload: { controlType: 'resume', taskCommand: { type: 'RESUME_TASK', taskKey: 'refund_ticket' } },
      status: 'PENDING',
    }
    apiMocks.proposeCustomerAssistantTaskControl.mockResolvedValue(proposedControl)
    apiMocks.listCustomerAssistantTasks.mockResolvedValue(mockCustomerAssistantTasks)
    apiMocks.listCustomerAssistantEvents.mockResolvedValue({
      list: [
        ...mockCustomerAssistantEvents.list,
        {
          id: 778,
          sessionId: 12,
          sequence: 2,
          type: 'task_control_proposed',
          source: 'operator_advisory',
          payload: { actionId: proposedControl.id },
        },
      ],
      total: 2,
    })
    apiMocks.listCustomerAssistantProposedActions.mockResolvedValue({ list: [proposedControl], total: 1 })

    const { createCustomerAssistantRuntimeState, proposeCustomerAssistantRuntimeTaskControl } = await import(
      './customerAssistantRuntime'
    )

    const state = await proposeCustomerAssistantRuntimeTaskControl(
      createCustomerAssistantRuntimeState({
        session: { id: 12, status: 'ACTIVE' },
        tasks: mockCustomerAssistantTasks.list,
      }),
      101,
      'resume',
      'customer supplied missing order number',
    )

    expect(apiMocks.proposeCustomerAssistantTaskControl).toHaveBeenCalledWith(12, 101, {
      controlType: 'resume',
      reason: 'customer supplied missing order number',
    })
    expect(apiMocks.listCustomerAssistantTasks).toHaveBeenCalledWith(12)
    expect(apiMocks.listCustomerAssistantEvents).toHaveBeenCalledWith(12)
    expect(apiMocks.listCustomerAssistantProposedActions).toHaveBeenCalledWith(12)
    expect(apiMocks.getCustomerAssistantSessionMetrics).toHaveBeenCalledWith(12)
    expect(state.proposedActions[0]).toMatchObject({
      id: 88,
      title: '恢复任务：refund_ticket',
      status: 'PENDING',
    })
    expect(state.eventTimeline.some((event) => event.title === 'task_control_proposed')).toBe(true)
  })
})
