import { get, patch, post } from '@/utils/request'

export interface CustomerAssistantListResult<T> {
  list: T[]
  total: number
}

export interface CustomerAssistantSession {
  id: number
  status: string
  context?: Record<string, unknown>
  version?: number
  createdAt?: string | null
  updatedAt?: string | null
}

export interface CustomerAssistantDemoStory {
  storyId: string
  title: string
  sessionId: number
  sessionStatus?: string
  customerName: string
  maskedPhone?: string
  openingMessage?: string
  taskCount: number
  pendingActionCount: number
  knowledgeBaseIds: number[]
  chatflowBindings?: Record<string, number>
}

export type CustomerAssistantTaskControlType = 'retry' | 'cancel' | 'resume'

export interface CustomerAssistantTaskControlPayload {
  controlType: CustomerAssistantTaskControlType
  reason?: string
}

export interface CustomerAssistantActionUpdatePayload {
  title?: string
  payload?: Record<string, unknown>
}

export interface CustomerAssistantWorkerProfile {
  profileId: string
  taskKey: string
  taskType: string
  workerType: string
  workerRef: string
  modelPolicyRef: string
  promptRef: string
  toolRefs: string[]
  riskPolicyRef: string
  enabled: boolean
}

export type CustomerAssistantWorkerProfileUpdatePayload = Omit<CustomerAssistantWorkerProfile, 'profileId'>

export interface CustomerAssistantSessionMetrics extends CustomerAssistantObservabilityMetrics {
  sessionId: number
}

export interface CustomerAssistantObservabilityMetrics {
  taskStatusCounts: Record<string, number>
  proposedActionStatusCounts: Record<string, number>
  humanConfirmation: {
    pending: number
    adopted: number
    terminal: number
    adoptionRate: number
  }
  eventCounts: {
    total: number
    byType: Record<string, number>
    bySource: Record<string, number>
  }
  workerEventCounts: {
    total: number
    byType: Record<string, number>
  }
  recentFailureReasons: CustomerAssistantFailureReason[]
}

export interface CustomerAssistantFailureReason {
  taskId: number
  taskType: string
  source: string
  reason: string
  storyId?: string
}

export interface CustomerAssistantDemoStoryMetricsStory extends CustomerAssistantObservabilityMetrics {
  storyId: string
  title: string
  sessionId: number
  sessionStatus: string
  taskCount: number
  pendingActionCount: number
  eventCount: number
  workerEventCount: number
}

export interface CustomerAssistantDemoStoryMetrics extends CustomerAssistantObservabilityMetrics {
  storyCount: number
  sessionCount: number
  stories: CustomerAssistantDemoStoryMetricsStory[]
}

export interface CustomerAssistantProposedAction {
  id: number
  sessionId?: number
  runId?: number
  taskId?: number | null
  actionKey?: string
  actionType: string
  title: string
  payload: Record<string, unknown>
  status: string
  result?: Record<string, unknown>
}

export interface CustomerAssistantTask {
  id: number
  sessionId: number
  taskKey: string
  taskType?: string
  businessKey?: string
  shortId?: string
  status: string
  workerType: string
  workerRef?: string
  checkpoint: Record<string, unknown>
  lastResult?: Record<string, unknown>
  proposedActions: CustomerAssistantProposedAction[]
  version?: number
}

export interface CustomerAssistantTaskSummary extends CustomerAssistantTask {}

export interface CustomerAssistantEvent {
  id: number
  sessionId: number
  runId?: number | null
  sequence: number
  type: string
  visibility?: string
  source?: string
  actor?: 'customer' | 'operator' | 'system'
  taskId?: number | null
  parentSpanId?: string | null
  spanId?: string | null
  payload: Record<string, unknown>
  createdAt?: string | null
}

export interface CustomerAssistantTurnResult {
  runId: number
  sessionId: number
  replyType: string
  operatorRecommendation: string
  customerReplyDraft: string
  taskSummaries: CustomerAssistantTaskSummary[]
  proposedActions: CustomerAssistantProposedAction[]
  warnings: string[]
  events: CustomerAssistantEvent[]
  replayed: boolean
}

export interface CustomerAssistantTurnPayload {
  message: string
  idempotencyKey?: string
  actor?: 'customer' | 'operator' | 'system'
}

export const createCustomerAssistantSession = (context: Record<string, unknown> = {}) =>
  post<CustomerAssistantSession>('/v1/customer-assistant/sessions', { context })

export const listCustomerAssistantDemoStories = () =>
  get<CustomerAssistantListResult<CustomerAssistantDemoStory>>('/v1/customer-assistant/demo-stories')

export const getCustomerAssistantDemoStoryMetrics = () =>
  get<CustomerAssistantDemoStoryMetrics>('/v1/customer-assistant/demo-stories/metrics')

export const listCustomerAssistantWorkerProfiles = () =>
  get<CustomerAssistantListResult<CustomerAssistantWorkerProfile>>('/v1/customer-assistant/worker-profiles')

export const updateCustomerAssistantWorkerProfile = (
  profileId: string,
  payload: CustomerAssistantWorkerProfileUpdatePayload,
) => patch<CustomerAssistantWorkerProfile>(`/v1/customer-assistant/worker-profiles/${profileId}`, payload)

export const sendCustomerAssistantTurn = (sessionId: number, payload: CustomerAssistantTurnPayload) => {
  const { message, idempotencyKey, actor } = payload
  return post<CustomerAssistantTurnResult>(`/v1/customer-assistant/sessions/${sessionId}/turns`, {
    message,
    idempotencyKey,
    ...(actor ? { actor } : {}),
  })
}

export const listCustomerAssistantTasks = (sessionId: number) =>
  get<CustomerAssistantListResult<CustomerAssistantTask>>(`/v1/customer-assistant/sessions/${sessionId}/tasks`)

export const listCustomerAssistantEvents = (sessionId: number) =>
  get<CustomerAssistantListResult<CustomerAssistantEvent>>(`/v1/customer-assistant/sessions/${sessionId}/events`)

export const listCustomerAssistantProposedActions = (sessionId: number) =>
  get<CustomerAssistantListResult<CustomerAssistantProposedAction>>(
    `/v1/customer-assistant/sessions/${sessionId}/proposed-actions`,
  )

export const getCustomerAssistantSessionMetrics = (sessionId: number) =>
  get<CustomerAssistantSessionMetrics>(`/v1/customer-assistant/sessions/${sessionId}/metrics`)

export const proposeCustomerAssistantTaskControl = (
  sessionId: number,
  taskId: number,
  payload: CustomerAssistantTaskControlPayload,
) =>
  post<CustomerAssistantProposedAction>(
    `/v1/customer-assistant/sessions/${sessionId}/tasks/${taskId}/controls/propose`,
    payload,
  )

export const confirmCustomerAssistantAction = (actionId: number) =>
  post<CustomerAssistantProposedAction>(`/v1/customer-assistant/proposed-actions/${actionId}/confirm`)

export const rejectCustomerAssistantAction = (actionId: number) =>
  post<CustomerAssistantProposedAction>(`/v1/customer-assistant/proposed-actions/${actionId}/reject`)

export const executeCustomerAssistantAction = (actionId: number) =>
  post<CustomerAssistantProposedAction>(`/v1/customer-assistant/proposed-actions/${actionId}/execute`)

export const updateCustomerAssistantAction = (actionId: number, payload: CustomerAssistantActionUpdatePayload) =>
  patch<CustomerAssistantProposedAction>(`/v1/customer-assistant/proposed-actions/${actionId}`, payload)
