import {
  confirmCustomerAssistantAction,
  createCustomerAssistantSession,
  executeCustomerAssistantAction,
  listCustomerAssistantEvents,
  listCustomerAssistantTasks,
  rejectCustomerAssistantAction,
  sendCustomerAssistantTurn,
  type CustomerAssistantEvent,
  type CustomerAssistantListResult,
  type CustomerAssistantSession,
  type CustomerAssistantTask,
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
    const { tasks, events } = await refreshCustomerAssistantRuntimeLedgers(session.id)
    return fromTurnResult(session, payload, turnResult, tasks.list, events.list)
  } finally {
    stream?.close()
  }
}

export async function refreshCustomerAssistantRuntimeLedgers(sessionId: number) {
  const [tasks, events] = await Promise.all([
    listCustomerAssistantTasks(sessionId),
    listCustomerAssistantEvents(sessionId),
  ])
  return { tasks, events }
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

function fromTurnResult(
  session: CustomerAssistantSession,
  payload: CustomerAssistantTurnPayload,
  turnResult: CustomerAssistantTurnResult,
  tasks: CustomerAssistantListResult<CustomerAssistantTask>['list'],
  events: CustomerAssistantListResult<CustomerAssistantEvent>['list'],
): CustomerAssistantRuntimeState {
  return {
    ...buildCustomerAssistantState({
      sessionId: session.id,
      customerInput: payload.actor === 'operator' ? undefined : payload.message,
      operatorInput: payload.actor === 'operator' ? payload.message : undefined,
      turnResult,
      tasks,
      events,
    }),
    session,
    tasks,
    events,
    loading: false,
    error: null,
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
  const { tasks, events } = await refreshCustomerAssistantRuntimeLedgers(current.session.id)
  const rebuilt = buildCustomerAssistantState({
    sessionId: current.session.id,
    tasks: tasks.list,
    events: events.list,
  })
  return {
    ...updated,
    taskSummary: rebuilt.taskSummary,
    eventTimeline: rebuilt.eventTimeline,
    progressStages: rebuilt.progressStages,
    tasks: tasks.list,
    events: events.list,
  }
}
