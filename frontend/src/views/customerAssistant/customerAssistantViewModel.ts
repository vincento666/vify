import type {
  CustomerAssistantEvent,
  CustomerAssistantProposedAction,
  CustomerAssistantSessionMetrics,
  CustomerAssistantTask,
  CustomerAssistantTaskControlType,
  CustomerAssistantTurnResult,
  CustomerAssistantWorkerProfile,
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
  workerRef?: string
  profile?: CustomerAssistantTaskProfile
  missingFields: string[]
  proposedActions: CustomerAssistantProposedAction[]
  availableControls: CustomerAssistantTaskControlType[]
  checkpoint: Record<string, unknown>
}

export interface CustomerAssistantTaskProfile {
  profileId: string
  modelPolicyRef: string
  promptRef: string
  toolRefs: string[]
  riskPolicyRef: string
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

export interface CustomerAssistantRecognitionEvidenceRow {
  key: string
  sequenceLabel: string
  taskKey: string
  taskType: string
  workerRoute: string
  profileId: string
  modelPolicyRef: string
  promptRef: string
  toolRefs: string[]
  riskPolicyRef: string
}

export interface CustomerAssistantProgressStage {
  key: 'recognizing' | 'workers' | 'recommendation' | 'ready'
  label: string
  status: 'pending' | 'active' | 'complete'
}

export interface CustomerAssistantMetricTile {
  key: 'adoption' | 'pending' | 'tasks' | 'events'
  label: string
  value: string
  tone: 'default' | 'processing' | 'success' | 'warning'
}

export interface CustomerAssistantFailureRow {
  taskId: number
  taskType: string
  source: string
  reason: string
}

export interface CustomerAssistantMetricsSummary {
  empty: boolean
  tiles: CustomerAssistantMetricTile[]
  failures: CustomerAssistantFailureRow[]
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
  recognitionEvidence: CustomerAssistantRecognitionEvidenceRow[]
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
  workerProfiles?: CustomerAssistantWorkerProfile[]
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
    taskSummary: summarizeCustomerAssistantTasks(tasks, input.workerProfiles),
    recommendation: {
      operatorRecommendation: turn?.operatorRecommendation ?? '',
      customerReplyDraft: turn?.customerReplyDraft ?? '',
      warnings: [...(turn?.warnings ?? [])],
    },
    proposedActions: [...(input.proposedActions ?? turn?.proposedActions ?? [])],
    eventTimeline: formatCustomerAssistantEvents(events),
    recognitionEvidence: formatTaskRecognitionEvidence(events),
    progressStages: deriveCustomerAssistantProgressStages(events),
    replayed: Boolean(turn?.replayed),
  }
}

export function summarizeCustomerAssistantTasks(
  tasks: CustomerAssistantTask[],
  workerProfiles: CustomerAssistantWorkerProfile[] = [],
): CustomerAssistantTaskSummaryModel {
  const counts: Record<string, number> = {}
  const items = tasks.map((task) => {
    const profile = taskWorkerProfile(task, workerProfiles)
    counts[task.status] = (counts[task.status] ?? 0) + 1
    return {
      id: task.id,
      displayName: taskDisplayName(task.taskKey),
      taskKey: task.taskKey,
      status: task.status,
      statusTone: statusTone(task.status),
      workerType: task.workerType,
      workerRef: task.workerRef,
      profile: profile ? taskProfile(profile) : undefined,
      missingFields: taskMissingFields(task),
      proposedActions: [...task.proposedActions],
      availableControls: availableTaskControls(task.status),
      checkpoint: { ...task.checkpoint },
    }
  })
  return { counts, items }
}

function taskWorkerProfile(
  task: CustomerAssistantTask,
  workerProfiles: CustomerAssistantWorkerProfile[],
): CustomerAssistantWorkerProfile | undefined {
  return (
    workerProfiles.find(
      (profile) =>
        taskMatchesProfile(task, profile) &&
        profile.workerType === task.workerType &&
        (!task.workerRef || profile.workerRef === task.workerRef),
    ) ?? workerProfiles.find((profile) => taskMatchesProfile(task, profile))
  )
}

function taskMatchesProfile(task: CustomerAssistantTask, profile: CustomerAssistantWorkerProfile): boolean {
  return task.taskKey === profile.taskKey || task.taskKey.startsWith(`${profile.taskKey}:`)
}

function taskProfile(profile: CustomerAssistantWorkerProfile): CustomerAssistantTaskProfile {
  return {
    profileId: profile.profileId,
    modelPolicyRef: profile.modelPolicyRef,
    promptRef: profile.promptRef,
    toolRefs: [...profile.toolRefs],
    riskPolicyRef: profile.riskPolicyRef,
  }
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

export function formatTaskRecognitionEvidence(
  events: CustomerAssistantEvent[],
): CustomerAssistantRecognitionEvidenceRow[] {
  return events.flatMap((event) => {
    if (event.type !== 'task_recognized') return []
    const commands = Array.isArray(event.payload.commands) ? event.payload.commands : []
    return commands.flatMap((value, index) => {
      const command = asRecord(value)
      if (!command) return []
      const profileRefs = asRecord(command.profileRefs)
      return [
        {
          key: `recognition-${event.id}-${index}`,
          sequenceLabel: `#${event.sequence}`,
          taskKey: stringField(command.taskKey, 'unknown_task'),
          taskType: stringField(command.taskType, 'unknown'),
          workerRoute: workerRoute(command),
          profileId: stringField(profileRefs?.profileId, '未配置'),
          modelPolicyRef: stringField(profileRefs?.modelPolicyRef, '未配置'),
          promptRef: stringField(profileRefs?.promptRef, '未配置'),
          toolRefs: stringListField(profileRefs?.toolRefs),
          riskPolicyRef: stringField(profileRefs?.riskPolicyRef, '未配置'),
        },
      ]
    })
  })
}

export function formatCustomerAssistantMetrics(
  metrics: CustomerAssistantSessionMetrics | null,
): CustomerAssistantMetricsSummary {
  const adoptionRate = metrics?.humanConfirmation.adoptionRate ?? 0
  const pending = metrics?.humanConfirmation.pending ?? 0
  const activeTasks = (metrics?.taskStatusCounts.RUNNING ?? 0) + (metrics?.taskStatusCounts.WAITING ?? 0)
  const eventTotal = metrics?.eventCounts.total ?? 0
  return {
    empty: metrics === null,
    tiles: [
      {
        key: 'adoption',
        label: '人工采纳率',
        value: `${Math.round(adoptionRate * 100)}%`,
        tone: adoptionRate > 0 ? 'success' : 'default',
      },
      {
        key: 'pending',
        label: '待确认动作',
        value: String(pending),
        tone: pending > 0 ? 'warning' : 'default',
      },
      {
        key: 'tasks',
        label: '活跃任务',
        value: String(activeTasks),
        tone: activeTasks > 0 ? 'processing' : 'default',
      },
      {
        key: 'events',
        label: '运行事件',
        value: String(eventTotal),
        tone: 'default',
      },
    ],
    failures: [...(metrics?.recentFailureReasons ?? [])],
  }
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

function availableTaskControls(status: string): CustomerAssistantTaskControlType[] {
  if (status === 'RUNNING' || status === 'PENDING') return ['cancel']
  if (status === 'WAITING') return ['resume', 'cancel']
  if (status === 'FAILED') return ['retry']
  return []
}

function taskMissingFields(task: CustomerAssistantTask): string[] {
  const lastResultFields = task.lastResult?.missingFields
  if (Array.isArray(lastResultFields)) return lastResultFields.map(String)

  const pendingPrompt = task.checkpoint.pendingPrompt
  if (typeof pendingPrompt === 'string' && pendingPrompt) return [pendingPrompt]

  return []
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function stringField(value: unknown, fallback: string): string {
  if (typeof value === 'string' && value.trim()) return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return fallback
}

function stringListField(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value
    .filter((item): item is string | number | boolean =>
      typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean',
    )
    .map(String)
}

function workerRoute(command: Record<string, unknown>): string {
  const workerType = stringField(command.workerType, 'unknown_worker')
  const workerRef = stringField(command.workerRef, '')
  return workerRef ? `${workerType} · ${workerRef}` : workerType
}

function hasAny(types: Set<string>, candidates: string[]): boolean {
  return candidates.some((type) => types.has(type))
}
