import type {
  CustomerAssistantEvent,
  CustomerAssistantProposedAction,
  CustomerAssistantTask,
  CustomerAssistantTurnResult,
} from '@/api/customerAssistant'

export interface CustomerAssistantLaneMessage {
  id: string
  lane: 'customer' | 'operator'
  role: 'customer' | 'operator' | 'assistant' | 'draft'
  source: 'customer' | 'operator' | 'assistant' | 'assistant-draft'
  content: string
  pending: boolean
  controls: string[]
}

export interface CustomerAssistantTaskRow {
  id: number
  displayName: string
  taskKey: string
  status: string
  statusTone: 'default' | 'processing' | 'success' | 'warning' | 'error'
  workerType: string
  missingFields: string[]
  proposedActions: CustomerAssistantProposedAction[]
  checkpoint: Record<string, unknown>
}

export interface CustomerAssistantTaskSummaryModel {
  counts: Record<string, number>
  items: CustomerAssistantTaskRow[]
}

export interface CustomerAssistantEventRow {
  key: string
  sequenceLabel: string
  title: string
  visibilityLabel: string
  sourceLabel: string
  payloadPreview: string
  debug: boolean
  defaultCollapsed: boolean
}

export interface CustomerAssistantProgressStage {
  key: 'recognizing' | 'workers' | 'recommendation' | 'ready'
  label: string
  status: 'pending' | 'active' | 'complete'
}

export interface CustomerAssistantRecommendationState {
  operatorRecommendation: string
  customerReplyDraft: string
  warnings: string[]
}

export interface CustomerAssistantDraftState {
  text: string
  applied: boolean
  outbound: boolean
  copyLabel: string
  applyLabel: string
}

export interface CustomerAssistantTurnStatusInput {
  loading?: boolean
  error?: string | null
  replayed?: boolean
}

export interface CustomerAssistantTurnStatus {
  kind: 'ready' | 'loading' | 'failed' | 'replayed'
  label: string
  detail?: string
}

export interface CustomerAssistantState {
  sessionId: number | null
  customerMessages: CustomerAssistantLaneMessage[]
  operatorMessages: CustomerAssistantLaneMessage[]
  taskSummary: CustomerAssistantTaskSummaryModel
  recommendation: CustomerAssistantRecommendationState
  proposedActions: CustomerAssistantProposedAction[]
  eventTimeline: CustomerAssistantEventRow[]
  progressStages: CustomerAssistantProgressStage[]
  replayed: boolean
}

export interface BuildCustomerAssistantStateInput {
  sessionId?: number | null
  customerInput?: string
  operatorInput?: string
  turnResult?: CustomerAssistantTurnResult | null
  tasks?: CustomerAssistantTask[]
  events?: CustomerAssistantEvent[]
  proposedActions?: CustomerAssistantProposedAction[]
}

export function buildCustomerAssistantState(input: BuildCustomerAssistantStateInput = {}): CustomerAssistantState {
  const turn = input.turnResult ?? null
  const sessionId = input.sessionId ?? turn?.sessionId ?? null
  const tasks = input.tasks ?? turn?.taskSummaries ?? []
  const events = input.events ?? turn?.events ?? []
  const customerMessages: CustomerAssistantLaneMessage[] = []
  const operatorMessages: CustomerAssistantLaneMessage[] = []

  if (input.customerInput) {
    customerMessages.push(message('customer-input', 'customer', 'customer', 'customer', input.customerInput, false))
  }
  if (turn?.customerReplyDraft) {
    customerMessages.push(message('customer-draft', 'customer', 'draft', 'assistant-draft', turn.customerReplyDraft, true))
  }
  if (input.operatorInput) {
    operatorMessages.push(message('operator-input', 'operator', 'operator', 'operator', input.operatorInput, false))
  }
  if (turn?.operatorRecommendation) {
    operatorMessages.push(
      message('operator-recommendation', 'operator', 'assistant', 'assistant', turn.operatorRecommendation, false),
    )
  }

  return {
    sessionId,
    customerMessages,
    operatorMessages,
    taskSummary: summarizeCustomerAssistantTasks(tasks),
    recommendation: {
      operatorRecommendation: turn?.operatorRecommendation ?? '',
      customerReplyDraft: turn?.customerReplyDraft ?? '',
      warnings: [...(turn?.warnings ?? [])],
    },
    proposedActions: [...(input.proposedActions ?? turn?.proposedActions ?? [])],
    eventTimeline: formatCustomerAssistantEvents(events),
    progressStages: deriveCustomerAssistantProgressStages(events),
    replayed: Boolean(turn?.replayed),
  }
}

export function summarizeCustomerAssistantTasks(tasks: CustomerAssistantTask[]): CustomerAssistantTaskSummaryModel {
  const counts: Record<string, number> = {}
  const items = tasks.map((task) => {
    counts[task.status] = (counts[task.status] ?? 0) + 1
    return {
      id: task.id,
      displayName: taskDisplayName(task.taskKey),
      taskKey: task.taskKey,
      status: task.status,
      statusTone: statusTone(task.status),
      workerType: task.workerType,
      missingFields: taskMissingFields(task),
      proposedActions: [...task.proposedActions],
      checkpoint: { ...task.checkpoint },
    }
  })
  return { counts, items }
}

export function applyCustomerAssistantActionState(
  state: CustomerAssistantState,
  action: CustomerAssistantProposedAction,
): CustomerAssistantState {
  const update = (item: CustomerAssistantProposedAction) => (item.id === action.id ? { ...item, ...action } : item)
  return {
    ...state,
    proposedActions: state.proposedActions.map(update),
    taskSummary: {
      ...state.taskSummary,
      items: state.taskSummary.items.map((item) => ({
        ...item,
        proposedActions: item.proposedActions.map(update),
      })),
    },
  }
}

export function formatCustomerAssistantEvents(events: CustomerAssistantEvent[]): CustomerAssistantEventRow[] {
  return events.map((event) => ({
    key: `event-${event.id}`,
    sequenceLabel: `#${event.sequence}`,
    title: event.type,
    visibilityLabel: event.visibility ?? 'normal',
    sourceLabel: event.source ?? 'system',
    payloadPreview: JSON.stringify(event.payload ?? {}),
    debug: event.visibility === 'debug',
    defaultCollapsed: event.visibility === 'debug',
  }))
}

export function deriveCustomerAssistantProgressStages(events: CustomerAssistantEvent[]): CustomerAssistantProgressStage[] {
  const types = new Set(events.map((event) => event.type))
  const recognizingComplete = hasAny(types, [
    'task_recognized',
    'task_added',
    'task_started',
    'worker_started',
    'recommendation_started',
    'run_completed',
  ])
  const workersComplete = hasAny(types, [
    'task_waiting',
    'task_completed',
    'task_failed',
    'recommendation_started',
    'recommendation_completed',
    'run_completed',
  ])
  const workersActive = !workersComplete && hasAny(types, ['task_added', 'task_started', 'worker_started'])
  const recommendationComplete = hasAny(types, ['recommendation_completed', 'recommendation_generated', 'run_completed'])
  const recommendationActive = !recommendationComplete && types.has('recommendation_started')
  return [
    {
      key: 'recognizing',
      label: 'Recognizing tasks',
      status: recognizingComplete ? 'complete' : types.has('run_started') ? 'active' : 'pending',
    },
    {
      key: 'workers',
      label: 'Running workers',
      status: workersComplete ? 'complete' : workersActive ? 'active' : 'pending',
    },
    {
      key: 'recommendation',
      label: 'Generating recommendation',
      status: recommendationComplete ? 'complete' : recommendationActive ? 'active' : 'pending',
    },
    {
      key: 'ready',
      label: 'Ready for operator',
      status: types.has('run_completed') ? 'complete' : 'pending',
    },
  ]
}

export function createCustomerAssistantDraftState(text: string, applied = false): CustomerAssistantDraftState {
  return {
    text,
    applied,
    outbound: false,
    copyLabel: '复制客户回复草稿',
    applyLabel: '本地应用客户回复草稿',
  }
}

export function applyCustomerAssistantDraftLocally(draft: CustomerAssistantDraftState): CustomerAssistantDraftState {
  return {
    ...draft,
    applied: true,
    outbound: false,
  }
}

export function formatCustomerAssistantTurnStatus(input: CustomerAssistantTurnStatusInput): CustomerAssistantTurnStatus {
  if (input.loading) {
    return { kind: 'loading', label: '正在请求客服助手' }
  }
  if (input.error) {
    return { kind: 'failed', label: '调用失败', detail: input.error }
  }
  if (input.replayed) {
    return { kind: 'replayed', label: '已复用幂等结果' }
  }
  return { kind: 'ready', label: '等待输入' }
}

function message(
  id: string,
  lane: CustomerAssistantLaneMessage['lane'],
  role: CustomerAssistantLaneMessage['role'],
  source: CustomerAssistantLaneMessage['source'],
  content: string,
  pending: boolean,
): CustomerAssistantLaneMessage {
  return {
    id,
    lane,
    role,
    source,
    content,
    pending,
    controls: lane === 'operator' ? ['inspect'] : [],
  }
}

function taskDisplayName(taskKey: string): string {
  const labels: Record<string, string> = {
    baggage_qa: '行李问答',
    refund_ticket: '退票处理',
  }
  return labels[taskKey] ?? taskKey
}

function statusTone(status: string): CustomerAssistantTaskRow['statusTone'] {
  if (status === 'COMPLETED') return 'success'
  if (status === 'WAITING') return 'warning'
  if (status === 'RUNNING' || status === 'PENDING') return 'processing'
  if (status === 'FAILED') return 'error'
  return 'default'
}

function taskMissingFields(task: CustomerAssistantTask): string[] {
  const lastResultFields = task.lastResult?.missingFields
  if (Array.isArray(lastResultFields)) return lastResultFields.map(String)

  const pendingPrompt = task.checkpoint.pendingPrompt
  if (typeof pendingPrompt === 'string' && pendingPrompt) return [pendingPrompt]

  return []
}

function hasAny(types: Set<string>, candidates: string[]): boolean {
  return candidates.some((type) => types.has(type))
}
