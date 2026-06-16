import {
  confirmCustomerAssistantAction,
  createCustomerAssistantSession,
  executeCustomerAssistantAction,
  listCustomerAssistantDemoStories,
  listCustomerAssistantEvents,
  listCustomerAssistantProposedActions,
  listCustomerAssistantTasks,
  proposeCustomerAssistantTaskControl,
  rejectCustomerAssistantAction,
  sendCustomerAssistantTurn,
  updateCustomerAssistantAction,
  type CustomerAssistantActionUpdatePayload,
  type CustomerAssistantDemoStory,
  type CustomerAssistantEvent,
  type CustomerAssistantListResult,
  type CustomerAssistantProposedAction,
  type CustomerAssistantSession,
  type CustomerAssistantTask,
  type CustomerAssistantTaskControlType,
  type CustomerAssistantTurnPayload,
  type CustomerAssistantTurnResult,
} from '@/api/customerAssistant'

import { openCustomerAssistantEventStream, type CustomerAssistantEventStream } from './customerAssistantEventStream'
import {
  applyCustomerAssistantActionState,
  buildCustomerAssistantState,
  type BuildCustomerAssistantStateInput,
  type CustomerAssistantState,
} from './customerAssistantViewModel'

export interface CustomerAssistantRuntimeState extends CustomerAssistantState {
  session: CustomerAssistantSession | null
  tasks: CustomerAssistantTask[]
  events: CustomerAssistantEvent[]
  loading: boolean
  error: string | null
}

export interface CreateCustomerAssistantRuntimeStateInput extends BuildCustomerAssistantStateInput {
  session?: CustomerAssistantSession | null
}

export interface SendCustomerAssistantRuntimeTurnOptions {
  onLiveState?: (state: CustomerAssistantRuntimeState) => void
}

export function createCustomerAssistantRuntimeState(
  input: CreateCustomerAssistantRuntimeStateInput = {},
): CustomerAssistantRuntimeState {
  const session = input.session ?? null
  return {
    ...buildCustomerAssistantState({
      ...input,
      sessionId: input.sessionId ?? session?.id ?? input.turnResult?.sessionId ?? null,
    }),
    session,
    tasks: input.tasks ?? input.turnResult?.taskSummaries ?? [],
    events: input.events ?? input.turnResult?.events ?? [],
    loading: false,
    error: null,
  }
}

export async function sendCustomerAssistantRuntimeTurn(
  current: CustomerAssistantRuntimeState,
  payload: CustomerAssistantTurnPayload,
  context: Record<string, unknown> = {},
  options: SendCustomerAssistantRuntimeTurnOptions = {},
): Promise<CustomerAssistantRuntimeState> {
  const session = current.session ?? await createCustomerAssistantSession(context)
  let liveState: CustomerAssistantRuntimeState = {
    ...current,
    session,
    loading: true,
    error: null,
  }
  let stream: CustomerAssistantEventStream | null = null
  stream = openCustomerAssistantEventStream(session.id, {
    afterSequence: lastEventSequence(liveState.events),
    onEvent: (event) => {
      liveState = mergeCustomerAssistantLiveEvent(liveState, event)
      options.onLiveState?.(liveState)
    },
    onError: (error) => {
      liveState = { ...liveState, error: error.message }
      options.onLiveState?.(liveState)
    },
  })
  try {
    const turnResult = await sendCustomerAssistantTurn(session.id, payload)
    const { tasks, events, proposedActions } = await refreshCustomerAssistantRuntimeLedgers(session.id)
    return fromTurnResult(session, payload, turnResult, tasks.list, events.list, proposedActions.list)
  } finally {
    stream?.close()
  }
}

export async function refreshCustomerAssistantRuntimeLedgers(sessionId: number) {
  const [tasks, events, proposedActions] = await Promise.all([
    listCustomerAssistantTasks(sessionId),
    listCustomerAssistantEvents(sessionId),
    listCustomerAssistantProposedActions(sessionId),
  ])
  return { tasks, events, proposedActions }
}

export async function loadCustomerAssistantDemoStory(storyId: string): Promise<CustomerAssistantRuntimeState> {
  const stories = await listCustomerAssistantDemoStories()
  const story = stories.list.find((item) => item.storyId === storyId)
  if (!story) {
    throw new Error(`Demo story not found: ${storyId}`)
  }
  const { tasks, events, proposedActions } = await refreshCustomerAssistantRuntimeLedgers(story.sessionId)
  const session = demoStorySession(story)
  return {
    ...buildCustomerAssistantState({
      sessionId: story.sessionId,
      customerInput: story.openingMessage,
      tasks: tasks.list,
      events: events.list,
      proposedActions: proposedActions.list,
    }),
    session,
    tasks: tasks.list,
    events: events.list,
    loading: false,
    error: null,
  }
}

export async function confirmCustomerAssistantRuntimeAction(
  current: CustomerAssistantRuntimeState,
  actionId: number,
): Promise<CustomerAssistantRuntimeState> {
  const action = await confirmCustomerAssistantAction(actionId)
  return applyRuntimeActionResult(current, action)
}

export async function rejectCustomerAssistantRuntimeAction(
  current: CustomerAssistantRuntimeState,
  actionId: number,
): Promise<CustomerAssistantRuntimeState> {
  const action = await rejectCustomerAssistantAction(actionId)
  return {
    ...applyCustomerAssistantActionState(current, action),
    session: current.session,
    tasks: current.tasks,
    events: current.events,
    loading: false,
    error: null,
  }
}

export async function executeCustomerAssistantRuntimeAction(
  current: CustomerAssistantRuntimeState,
  actionId: number,
): Promise<CustomerAssistantRuntimeState> {
  const action = await executeCustomerAssistantAction(actionId)
  return {
    ...applyCustomerAssistantActionState(current, action),
    session: current.session,
    tasks: current.tasks,
    events: current.events,
    loading: false,
    error: null,
  }
}

export async function updateCustomerAssistantRuntimeAction(
  current: CustomerAssistantRuntimeState,
  actionId: number,
  payload: CustomerAssistantActionUpdatePayload,
): Promise<CustomerAssistantRuntimeState> {
  const action = await updateCustomerAssistantAction(actionId, payload)
  return {
    ...applyCustomerAssistantActionState(current, action),
    session: current.session,
    tasks: current.tasks,
    events: current.events,
    loading: false,
    error: null,
  }
}

export async function proposeCustomerAssistantRuntimeTaskControl(
  current: CustomerAssistantRuntimeState,
  taskId: number,
  controlType: CustomerAssistantTaskControlType,
  reason = '',
): Promise<CustomerAssistantRuntimeState> {
  if (!current.session?.id) {
    throw new Error('Customer assistant session is required before proposing a task control')
  }
  await proposeCustomerAssistantTaskControl(current.session.id, taskId, { controlType, reason })
  const { tasks, events, proposedActions } = await refreshCustomerAssistantRuntimeLedgers(current.session.id)
  const rebuilt = buildCustomerAssistantState({
    sessionId: current.session.id,
    tasks: tasks.list,
    events: events.list,
    proposedActions: proposedActions.list,
  })
  return {
    ...rebuilt,
    session: current.session,
    tasks: tasks.list,
    events: events.list,
    loading: false,
    error: null,
  }
}

function fromTurnResult(
  session: CustomerAssistantSession,
  payload: CustomerAssistantTurnPayload,
  turnResult: CustomerAssistantTurnResult,
  tasks: CustomerAssistantListResult<CustomerAssistantTask>['list'],
  events: CustomerAssistantListResult<CustomerAssistantEvent>['list'],
  proposedActions: CustomerAssistantListResult<CustomerAssistantProposedAction>['list'],
): CustomerAssistantRuntimeState {
  return {
    ...buildCustomerAssistantState({
      sessionId: session.id,
      customerInput: payload.actor === 'operator' ? undefined : payload.message,
      operatorInput: payload.actor === 'operator' ? payload.message : undefined,
      turnResult,
      tasks,
      events,
      proposedActions,
    }),
    session,
    tasks,
    events,
    loading: false,
    error: null,
  }
}

function demoStorySession(story: CustomerAssistantDemoStory): CustomerAssistantSession {
  return {
    id: story.sessionId,
    status: story.sessionStatus ?? 'ACTIVE',
    context: {
      demoSeed: '073',
      storyId: story.storyId,
      storyTitle: story.title,
      customer: {
        name: story.customerName,
        phone: story.maskedPhone ?? '',
      },
      openingMessage: story.openingMessage ?? '',
      knowledgeBaseIds: story.knowledgeBaseIds,
      chatflowBindings: story.chatflowBindings ?? {},
    },
  }
}

export function mergeCustomerAssistantLiveEvent(
  current: CustomerAssistantRuntimeState,
  event: CustomerAssistantEvent,
): CustomerAssistantRuntimeState {
  const events = mergeEvents(current.events, event)
  const tasks = mergeLiveTask(current.tasks, event)
  return {
    ...buildCustomerAssistantState({
      sessionId: current.session?.id ?? current.sessionId,
      tasks,
      events,
    }),
    session: current.session,
    tasks,
    events,
    loading: current.loading,
    error: current.error,
  }
}

function mergeEvents(events: CustomerAssistantEvent[], event: CustomerAssistantEvent): CustomerAssistantEvent[] {
  if (events.some((item) => item.id === event.id || item.sequence === event.sequence)) return events
  return [...events, event].sort((left, right) => left.sequence - right.sequence)
}

function mergeLiveTask(tasks: CustomerAssistantTask[], event: CustomerAssistantEvent): CustomerAssistantTask[] {
  const taskKey = liveTaskKey(event)
  if (!taskKey) return tasks
  const status = liveTaskStatus(event.type)
  const workerType = String(event.payload?.workerType || event.source || 'customer_assistant')
  const taskId = Number(event.taskId || event.payload?.taskId || event.sequence)
  const existing = tasks.find((task) => task.taskKey === taskKey || task.id === taskId)
  if (existing) {
    return tasks.map((task) =>
      task === existing
        ? {
            ...task,
            status: status ?? task.status,
            workerType: task.workerType || workerType,
          }
        : task,
    )
  }
  if (!status) return tasks
  return [
    ...tasks,
    {
      id: taskId,
      sessionId: event.sessionId,
      taskKey,
      taskType: String(event.payload?.taskType || taskKey),
      businessKey: String(event.payload?.businessKey || taskKey),
      shortId: taskKey,
      status,
      workerType,
      workerRef: String(event.payload?.workerRef || taskKey),
      checkpoint: {},
      lastResult: {},
      proposedActions: [],
    },
  ]
}

function liveTaskKey(event: CustomerAssistantEvent): string {
  const payload = event.payload || {}
  if (typeof payload.taskKey === 'string') return payload.taskKey
  const commands = payload.commands
  if (Array.isArray(commands) && typeof commands[0]?.taskKey === 'string') return commands[0].taskKey
  return ''
}

function liveTaskStatus(eventType: string): string | null {
  if (['task_added', 'task_recognized'].includes(eventType)) return 'PENDING'
  if (['task_started', 'worker_started'].includes(eventType)) return 'RUNNING'
  if (eventType === 'task_waiting') return 'WAITING'
  if (eventType === 'task_completed') return 'COMPLETED'
  if (eventType === 'task_failed') return 'FAILED'
  return null
}

function lastEventSequence(events: CustomerAssistantEvent[]): number {
  return events.reduce((max, event) => Math.max(max, event.sequence), 0)
}

async function applyRuntimeActionResult(
  current: CustomerAssistantRuntimeState,
  action: Awaited<ReturnType<typeof confirmCustomerAssistantAction>>,
): Promise<CustomerAssistantRuntimeState> {
  const updated = {
    ...applyCustomerAssistantActionState(current, action),
    session: current.session,
    tasks: current.tasks,
    events: current.events,
    loading: false,
    error: null,
  }
  if (action.actionType !== 'PROPOSED_TASK_COMMAND' || !current.session?.id) return updated
  const { tasks, events, proposedActions } = await refreshCustomerAssistantRuntimeLedgers(current.session.id)
  const rebuilt = buildCustomerAssistantState({
    sessionId: current.session.id,
    tasks: tasks.list,
    events: events.list,
    proposedActions: proposedActions.list,
  })
  return {
    ...updated,
    taskSummary: rebuilt.taskSummary,
    eventTimeline: rebuilt.eventTimeline,
    progressStages: rebuilt.progressStages,
    proposedActions: rebuilt.proposedActions,
    tasks: tasks.list,
    events: events.list,
  }
}
