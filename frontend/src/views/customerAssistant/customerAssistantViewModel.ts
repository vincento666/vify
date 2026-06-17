import type {
  CustomerAssistantEvent,
  CustomerAssistantObservabilityMetrics,
  CustomerAssistantOperatorAudit,
  CustomerAssistantOperatorAuditRow as CustomerAssistantOperatorAuditApiRow,
  CustomerAssistantOperatorKnowledgeQaResult,
  CustomerAssistantProposedAction,
  CustomerAssistantTask,
  CustomerAssistantTaskControlType,
  CustomerAssistantTurnResult,
  CustomerAssistantWorkerAsyncRefs,
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
  workerAsyncRefs?: CustomerAssistantWorkerAsyncRefs
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
  toolPolicyRef: string
  riskPolicyRef: string
  outputSchemaRef: string
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

export interface CustomerAssistantOperatorAuditRow {
  key: string
  sequenceLabel: string
  title: string
  status: string
  actorLabel: string
  sourceLabel: string
  targetLabel: string
  summary: string
  createdAt: string
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

export interface CustomerAssistantOperatorAdvisoryEvidenceRow {
  key: string
  sequenceLabel: string
  turnMode: string
  taskCount: number
  eventCount: number
  evidenceCount: number
  knowledgeSnippetCount: number
  warnings: string[]
}

export interface CustomerAssistantOperatorKnowledgeQaSourceRow {
  key: string
  title: string
  meta: string
  score: string
  excerpt: string
}

export interface CustomerAssistantOperatorKnowledgeQaEvidenceRow {
  key: string
  label: string
  detail: string
}

export interface CustomerAssistantOperatorKnowledgeQaContextRow {
  key: string
  label: string
  value: string
}

export interface CustomerAssistantOperatorKnowledgeQaState {
  empty: boolean
  question: string
  answer: string
  sourceRows: CustomerAssistantOperatorKnowledgeQaSourceRow[]
  evidenceRows: CustomerAssistantOperatorKnowledgeQaEvidenceRow[]
  contextRows: CustomerAssistantOperatorKnowledgeQaContextRow[]
  warnings: string[]
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

export interface CustomerAssistantEvalTile {
  key: 'taskHits' | 'workerRuns' | 'modelEvidence' | 'adoption'
  label: string
  value: string
  detail: string
  tone: 'default' | 'processing' | 'success' | 'warning' | 'error'
}

export interface CustomerAssistantEvalEvidenceRow {
  key: string
  title: string
  detail: string
  meta: string[]
  tone: 'default' | 'processing' | 'success' | 'warning' | 'error'
}

export interface CustomerAssistantModelEvidenceRow {
  key: string
  title: string
  detail: string
  reason: string
  tone: 'default' | 'success' | 'warning' | 'error'
}

export interface CustomerAssistantEvalSurfaceInput {
  taskSummary: CustomerAssistantTaskSummaryModel
  recognitionEvidence: CustomerAssistantRecognitionEvidenceRow[]
  events: CustomerAssistantEvent[]
  metrics: CustomerAssistantObservabilityMetrics | null
}

export interface CustomerAssistantEvalSurface {
  empty: boolean
  tiles: CustomerAssistantEvalTile[]
  taskRecognition: CustomerAssistantEvalEvidenceRow[]
  workerExecution: CustomerAssistantEvalEvidenceRow[]
  modelEvidence: CustomerAssistantModelEvidenceRow[]
  failures: CustomerAssistantFailureRow[]
}

export interface CustomerAssistantActionReceiptRow {
  key: string
  label: string
  value: string
}

export interface CustomerAssistantActionReceipt {
  visible: boolean
  executorRef: string
  semanticCode: string
  executedAt: string
  error: string
  auditRows: CustomerAssistantActionReceiptRow[]
}

export interface CustomerAssistantActionDecisionReceipt {
  visible: boolean
  tone: 'success' | 'error' | 'default'
  statusLabel: string
  note: string
  reason: string
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
  operatorAuditRows: CustomerAssistantOperatorAuditRow[]
  recognitionEvidence: CustomerAssistantRecognitionEvidenceRow[]
  operatorAdvisoryEvidence: CustomerAssistantOperatorAdvisoryEvidenceRow[]
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
  operatorAudit?: CustomerAssistantOperatorAudit | null
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
    operatorAuditRows: formatCustomerAssistantOperatorAudit(input.operatorAudit),
    recognitionEvidence: formatTaskRecognitionEvidence(events),
    operatorAdvisoryEvidence: formatOperatorAdvisoryEvidence(events),
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
      workerAsyncRefs: taskWorkerAsyncRefs(task),
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
    toolPolicyRef: profile.toolPolicyRef ?? 'customer_assistant_worker_tool_default',
    riskPolicyRef: profile.riskPolicyRef,
    outputSchemaRef: profile.outputSchemaRef ?? 'customer_assistant_worker_result_v1',
  }
}

function taskWorkerAsyncRefs(task: CustomerAssistantTask): CustomerAssistantWorkerAsyncRefs | undefined {
  const direct = task.workerAsyncRefs
  if (direct?.supported) return direct
  const lastResultRefs = asRecord(task.lastResult?.workerAsyncRefs)
  if (!lastResultRefs?.supported) return undefined
  return {
    supported: true,
    workerRunId: stringField(lastResultRefs.workerRunId, ''),
    workerStatusRef: stringField(lastResultRefs.workerStatusRef, ''),
    workerEventsRef: stringField(lastResultRefs.workerEventsRef, ''),
    workerEventStreamRef: stringField(lastResultRefs.workerEventStreamRef, ''),
    workerResultRef: stringField(lastResultRefs.workerResultRef, ''),
    reason: stringField(lastResultRefs.reason, ''),
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

export function formatCustomerAssistantActionReceipt(
  action: CustomerAssistantProposedAction,
): CustomerAssistantActionReceipt {
  const result = asRecord(action.result)
  const audit = asRecord(result?.audit)
  const visible = action.status === 'EXECUTED' || action.status === 'FAILED'
  if (!visible || !result) {
    return {
      visible: false,
      executorRef: '',
      semanticCode: '',
      executedAt: '',
      error: '',
      auditRows: [],
    }
  }
  return {
    visible: true,
    executorRef: stringField(result.executorRef, '未记录'),
    semanticCode: stringField(audit?.semanticCode, action.status),
    executedAt: stringField(audit?.executedAt, ''),
    error: stringField(result.error, ''),
    auditRows: Object.entries(audit ?? {})
      .filter(([key, value]) => key !== 'semanticCode' && key !== 'executedAt' && value !== null && value !== undefined)
      .map(([key, value]) => ({
        key,
        label: key,
        value: receiptValue(value),
      })),
  }
}

export function formatCustomerAssistantActionDecisionReceipt(
  action: CustomerAssistantProposedAction,
): CustomerAssistantActionDecisionReceipt {
  const result = asRecord(action.result)
  const decision = asRecord(result?.decision)
  const note = stringField(decision?.note, '')
  const reason = stringField(decision?.reason, '')
  const visible = ['CONFIRMED', 'REJECTED'].includes(action.status) && Boolean(note || reason)
  return {
    visible,
    tone: action.status === 'REJECTED' ? 'error' : visible ? 'success' : 'default',
    statusLabel: action.status === 'REJECTED' ? '已拒绝' : action.status === 'CONFIRMED' ? '已确认' : '',
    note,
    reason,
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

export function formatCustomerAssistantOperatorAudit(
  audit: CustomerAssistantOperatorAudit | null | undefined,
): CustomerAssistantOperatorAuditRow[] {
  return (audit?.list ?? []).map((row) => ({
    key: `audit-${row.id}`,
    sequenceLabel: `#${row.sequence}`,
    title: row.title,
    status: row.status,
    actorLabel: row.actor || 'system',
    sourceLabel: row.source || 'customer_assistant',
    targetLabel: auditTargetLabel(row),
    summary: row.summary,
    createdAt: row.createdAt ?? '',
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

export function formatOperatorAdvisoryEvidence(
  events: CustomerAssistantEvent[],
): CustomerAssistantOperatorAdvisoryEvidenceRow[] {
  return events.flatMap((event) => {
    if (event.type !== 'operator_advisory_context_packed') return []
    const payload = asRecord(event.payload) ?? {}
    return [
      {
        key: `advisory-${event.id}`,
        sequenceLabel: `#${event.sequence}`,
        turnMode: stringField(payload.turnMode, 'operator_recommendation'),
        taskCount: numberField(payload.taskCount),
        eventCount: numberField(payload.eventCount),
        evidenceCount: numberField(payload.evidenceCount),
        knowledgeSnippetCount: numberField(payload.knowledgeSnippetCount),
        warnings: stringListField(payload.warnings),
      },
    ]
  })
}

export function formatCustomerAssistantOperatorKnowledgeQa(
  qa: CustomerAssistantOperatorKnowledgeQaResult | null | undefined,
): CustomerAssistantOperatorKnowledgeQaState {
  if (!qa) {
    return {
      empty: true,
      question: '',
      answer: '',
      sourceRows: [],
      evidenceRows: [],
      contextRows: [],
      warnings: [],
    }
  }
  return {
    empty: false,
    question: redactOperatorKnowledgeText(qa.question),
    answer: redactOperatorKnowledgeText(qa.answer),
    sourceRows: qa.sources.map((source, index) => ({
      key: `source-${source.knowledgeBaseId}-${source.faqId ?? source.documentId ?? source.chunkId ?? index}`,
      title: redactOperatorKnowledgeText(stringField(source.title, '未命名来源')),
      meta: [
        redactOperatorKnowledgeText(stringField(source.sourceType, 'SOURCE')),
        redactOperatorKnowledgeText(stringField(source.matchType, 'match')),
        `KB ${source.knowledgeBaseId}`,
      ].join(' · '),
      score: source.score === undefined ? '' : String(source.score),
      excerpt: redactOperatorKnowledgeText(stringField(source.answerExcerpt, '')),
    })),
    evidenceRows: qa.evidence.map((item, index) => {
      const taskKey = redactOperatorKnowledgeText(stringField(item.taskKey, item.type))
      return {
        key: `evidence-${index}-${taskKey}`,
        label: [
          redactOperatorKnowledgeText(stringField(item.taskType, item.type)),
          redactOperatorKnowledgeText(stringField(item.status, 'UNKNOWN')),
        ].join(' · '),
        detail: [
          taskKey,
          redactOperatorKnowledgeText(stringField(item.workerRef, item.workerType ?? '')),
          redactOperatorKnowledgeText(stringField(item.currentStep, item.sopId ?? '')),
        ]
          .filter(Boolean)
          .join(' · '),
      }
    }),
    contextRows: operatorKnowledgeContextRows(qa.contextSummary),
    warnings: qa.warnings.map(redactOperatorKnowledgeText),
  }
}

export function formatCustomerAssistantMetrics(
  metrics: CustomerAssistantObservabilityMetrics | null,
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

export function formatCustomerAssistantEvalSurface(
  input: CustomerAssistantEvalSurfaceInput,
): CustomerAssistantEvalSurface {
  const workerCounts = input.metrics?.workerEventCounts.byType ?? countWorkerEvents(input.events)
  const workerStarted = numberMetric(workerCounts, 'worker_started')
  const workerResult =
    numberMetric(workerCounts, 'worker_result_received') +
    numberMetric(workerCounts, 'worker_result_consumed') +
    numberMetric(workerCounts, 'task_waiting') +
    numberMetric(workerCounts, 'task_completed')
  const workerFailed =
    numberMetric(workerCounts, 'worker_failed') +
    numberMetric(workerCounts, 'worker_timed_out') +
    numberMetric(workerCounts, 'task_failed')
  const workerTotal = input.metrics?.workerEventCounts.total ?? workerStarted + workerResult + workerFailed
  const modelEvidence = formatModelEvidence(input.events)
  const diffCount = modelEvidence.filter((row) => row.reason === 'diff mismatch' || row.reason === 'baseline match').length
  const fallbackCount = modelEvidence.filter((row) => row.title === '模型回退').length
  const adoption = input.metrics?.humanConfirmation ?? { pending: 0, adopted: 0, terminal: 0, adoptionRate: 0 }
  const taskKeys = input.recognitionEvidence.map((row) => row.taskKey)
  return {
    empty:
      input.recognitionEvidence.length === 0 &&
      input.taskSummary.items.length === 0 &&
      modelEvidence.length === 0 &&
      input.metrics === null,
    tiles: [
      {
        key: 'taskHits',
        label: '任务命中',
        value: String(input.recognitionEvidence.length),
        detail: taskKeys.length ? taskKeys.join('、') : 'no recognized task',
        tone: input.recognitionEvidence.length > 0 ? 'success' : 'default',
      },
      {
        key: 'workerRuns',
        label: 'Worker 执行',
        value: String(workerTotal),
        detail: `started ${workerStarted} · result ${workerResult} · failed ${workerFailed}`,
        tone: workerFailed > 0 ? 'error' : workerTotal > 0 ? 'processing' : 'default',
      },
      {
        key: 'modelEvidence',
        label: '模型证据',
        value: String(modelEvidence.length),
        detail: `diff ${diffCount} · fallback ${fallbackCount}`,
        tone: fallbackCount > 0 || diffCount > 0 ? 'warning' : modelEvidence.length > 0 ? 'success' : 'default',
      },
      {
        key: 'adoption',
        label: '采纳率',
        value: `${Math.round(adoption.adoptionRate * 100)}%`,
        detail: `${adoption.adopted}/${adoption.terminal} adopted · pending ${adoption.pending}`,
        tone: adoption.adopted > 0 ? 'success' : adoption.pending > 0 ? 'warning' : 'default',
      },
    ],
    taskRecognition: input.recognitionEvidence.map((row) => ({
      key: row.key,
      title: row.taskKey,
      detail: `${row.taskType} · ${row.workerRoute}`,
      meta: [
        `模型 ${row.modelPolicyRef}`,
        `提示词 ${row.promptRef}`,
        `风险 ${row.riskPolicyRef}`,
      ],
      tone: row.profileId === '未配置' ? 'warning' : 'success',
    })),
    workerExecution: input.taskSummary.items.map((task) => ({
      key: `worker-${task.id}`,
      title: task.displayName,
      detail: `${task.taskKey} · ${task.workerType}${task.workerRef ? ` · ${task.workerRef}` : ''}`,
      meta: [
        task.status,
        ...(task.missingFields.length ? [`缺失 ${task.missingFields.join('、')}`] : []),
      ],
      tone: task.statusTone,
    })),
    modelEvidence,
    failures: (input.metrics?.recentFailureReasons ?? []).map((failure) => ({
      ...failure,
      reason: redactEvalText(failure.reason),
    })),
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

function receiptValue(value: unknown): string {
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}

function auditTargetLabel(row: CustomerAssistantOperatorAuditApiRow): string {
  const targetType = row.targetType || 'session'
  return row.targetId === null || row.targetId === undefined ? targetType : `${targetType} #${row.targetId}`
}

function numberField(value: unknown): number {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

function numberMetric(counts: Record<string, number>, key: string): number {
  return Number(counts[key] ?? 0)
}

function countWorkerEvents(events: CustomerAssistantEvent[]): Record<string, number> {
  const workerTypes = new Set([
    'worker_started',
    'worker_result_received',
    'worker_result_consumed',
    'worker_failed',
    'worker_timed_out',
    'task_waiting',
    'task_completed',
    'task_failed',
  ])
  const counts: Record<string, number> = {}
  for (const event of events) {
    if (!workerTypes.has(event.type)) continue
    counts[event.type] = (counts[event.type] ?? 0) + 1
  }
  return counts
}

function formatModelEvidence(events: CustomerAssistantEvent[]): CustomerAssistantModelEvidenceRow[] {
  return events.flatMap((event): CustomerAssistantModelEvidenceRow[] => {
    const payload = asRecord(event.payload) ?? {}
    const phase = redactEvalText(stringField(payload.phase, 'recommendation'))
    if (event.type === 'llm_shadow_diff_recorded') {
      const diff = asRecord(payload.diff)
      const matches = Boolean(diff?.matches)
      const differences = stringListField(diff?.differences).map(redactEvalText)
      const title = phase === 'recommendation'
        ? matches ? '推荐影子一致' : '推荐影子差异'
        : matches ? '识别影子一致' : '识别影子差异'
      return [
        {
          key: `model-${event.id}`,
          title,
          detail: `${phase} · ${matches ? 'matches' : differences.join('、') || 'difference'}`,
          reason: matches ? 'baseline match' : 'diff mismatch',
          tone: matches ? 'success' : 'warning',
        },
      ]
    }
    if (event.type === 'llm_primary_fallback' || event.type === 'two_stage_fallback') {
      const reason = redactEvalText(stringField(payload.reason, 'fallback'))
      return [
        {
          key: `model-${event.id}`,
          title: '模型回退',
          detail: `${phase} · ${reason}`,
          reason,
          tone: 'warning',
        },
      ]
    }
    if (event.type === 'llm_primary_selected' || event.type === 'two_stage_primary_selected') {
      const selectedSource = redactEvalText(stringField(payload.selectedSource, event.source ?? 'model'))
      return [
        {
          key: `model-${event.id}`,
          title: '模型路径选中',
          detail: `${phase} · ${selectedSource}`,
          reason: 'selected',
          tone: 'success',
        },
      ]
    }
    if (event.type === 'llm_shadow_failed') {
      const error = redactEvalText(stringField(payload.error, 'shadow failed'))
      return [
        {
          key: `model-${event.id}`,
          title: '影子评估失败',
          detail: `${phase} · ${error}`,
          reason: error,
          tone: 'error',
        },
      ]
    }
    return []
  })
}

function redactEvalText(value: string): string {
  return value
    .replace(/api[_-]?key\s*=\s*[^,\s;]+/gi, 'api_key=[REDACTED]')
    .replace(/sk-[A-Za-z0-9._-]+/g, '[REDACTED]')
    .replace(/\b1[3-9]\d{9}\b/g, '[REDACTED]')
}

function workerRoute(command: Record<string, unknown>): string {
  const workerType = stringField(command.workerType, 'unknown_worker')
  const workerRef = stringField(command.workerRef, '')
  return workerRef ? `${workerType} · ${workerRef}` : workerType
}

function hasAny(types: Set<string>, candidates: string[]): boolean {
  return candidates.some((type) => types.has(type))
}

function operatorKnowledgeContextRows(
  context: CustomerAssistantOperatorKnowledgeQaResult['contextSummary'],
): CustomerAssistantOperatorKnowledgeQaContextRow[] {
  const rows: CustomerAssistantOperatorKnowledgeQaContextRow[] = []
  const pushNumber = (key: string, label: string, value: unknown) => {
    if (value === undefined || value === null) return
    rows.push({ key, label, value: String(numberField(value)) })
  }
  const pushText = (key: string, label: string, value: unknown) => {
    const text = redactOperatorKnowledgeText(stringField(value, ''))
    if (text) rows.push({ key, label, value: text })
  }
  pushText('storyTitle', '故事线', context.storyTitle)
  const customer = asRecord(context.customer)
  const customerName = redactOperatorKnowledgeText(stringField(customer?.name, ''))
  const maskedPhone = redactOperatorKnowledgeText(stringField(customer?.maskedPhone, ''))
  if (customerName || maskedPhone) {
    rows.push({
      key: 'customer',
      label: '客户',
      value: [customerName, maskedPhone].filter(Boolean).join(' · '),
    })
  }
  pushNumber('taskCount', '任务数', context.taskCount)
  pushNumber('pendingActionCount', '待确认动作', context.pendingActionCount)
  pushNumber('eventCount', '事件数', context.eventCount)
  if (Array.isArray(context.knowledgeBaseIds) && context.knowledgeBaseIds.length) {
    rows.push({
      key: 'knowledgeBaseIds',
      label: '知识库',
      value: context.knowledgeBaseIds.map(String).join('、'),
    })
  }
  if (Array.isArray(context.latestEventTypes) && context.latestEventTypes.length) {
    rows.push({
      key: 'latestEventTypes',
      label: '最近事件',
      value: context.latestEventTypes.map((item) => redactOperatorKnowledgeText(String(item))).join('、'),
    })
  }
  return rows
}

function redactOperatorKnowledgeText(value: string): string {
  return value
    .replace(/(api[_-]?key=)[^\s;]+/gi, '$1[REDACTED]')
    .replace(/\b1[3-9]\d{9}\b/g, '[REDACTED]')
    .replace(/(:)[A-Z]{2,}\d[\w-]*/g, '$1[REDACTED]')
    .replace(/\b[A-Z]{2,}\d{2,}-\d{2,}\b/g, '[REDACTED]')
}
