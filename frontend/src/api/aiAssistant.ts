import { del, get, post } from '@/utils/request'

export interface AiAssistantSession {
  id: number
  title: string
  status: string
  context?: Record<string, unknown>
  createdAt?: string
  updatedAt?: string
}

export interface AiAssistantRunEventList {
  list: AiAssistantEvent[]
  total: number
}

export interface AiAssistantListResult<T> {
  list: T[]
  total: number
}

export interface AiAssistantEvent {
  id: number
  sessionId: number
  runId: number
  taskId?: number | null
  toolCallId?: number | null
  sequence: number
  type: string
  level: string
  status: string
  visibleTitle: string
  visibleSummary: string
  payload: Record<string, unknown>
  correlationIds?: Record<string, unknown>
  createdAt: string
}

export interface AiAssistantRun {
  id: number
  sessionId: number
  status: string
  input: Record<string, unknown>
  result: Record<string, unknown>
  startedAt?: string | null
  completedAt?: string | null
}

export interface AiAssistantPlanStep {
  id: string
  title: string
  status: string
  toolName?: string | null
  sequence: number
}

export interface AiAssistantPlan {
  id: string
  planningStrategy: 'auto_lightweight' | 'deliberate' | 'plan_only' | string
  status: string
  recognizedNeeds: string[]
  steps: AiAssistantPlanStep[]
  currentStep?: AiAssistantPlanStep | null
  plannedTools: string[]
  finalResult?: string
}

export interface AiAssistantTurnResult {
  runId: number
  sessionId: number
  status: string
  replayed: boolean
  planningStrategy?: string
  plan?: AiAssistantPlan
  finalAnswer: string
  toolCalls: AiAssistantToolCall[]
  approvalRequired?: boolean
  approvalId?: number | null
  sandboxDenied?: boolean
  eventStreamRef?: string
}

export interface AiAssistantToolCall {
  id: number
  toolName: string
  input: Record<string, unknown>
  output: Record<string, unknown>
  status: string
  durationMs: number
}

export interface SendAiAssistantMessagePayload {
  message: string
  idempotencyKey?: string
  planningStrategy?: string
  approvalMode?: string
  modelMode?: string
  toolName?: string
  toolInput?: Record<string, unknown>
  toolCalls?: Array<{ toolName: string; toolInput?: Record<string, unknown> }>
  modelConfig?: AiAssistantModelConfigPayload
}

export interface AiAssistantModelConfigPayload {
  provider?: string
  baseUrl?: string
  model?: string
  apiKey?: string
  apiKeyRef?: string
  temperature?: number
  maxTokens?: number
}

export interface AiAssistantRuntimeConfig {
  modelMode?: 'deterministic' | 'live'
  modelName: string
  baseUrl: string
  apiKey: string
  temperature: number
  maxTokens: number
  streamEnabled: boolean
}

export type AiAssistantApprovalMode = 'ask_each_time' | 'smart_approval' | 'always_approve'

export function buildAiAssistantMessagePayload(
  message: string,
  runtimeConfig: AiAssistantRuntimeConfig,
  idempotencyKey: string,
  approvalMode: AiAssistantApprovalMode = 'smart_approval',
): SendAiAssistantMessagePayload {
  const basePayload = {
    message,
    idempotencyKey,
    planningStrategy: 'auto_lightweight',
    approvalMode,
  }
  if (runtimeConfig.modelMode === 'deterministic') {
    return {
      ...basePayload,
      modelMode: 'deterministic',
    }
  }
  return {
    ...basePayload,
    modelMode: 'live',
    modelConfig: {
      provider: 'openrouter',
      baseUrl: runtimeConfig.baseUrl,
      model: runtimeConfig.modelName,
      apiKey: runtimeConfig.apiKey,
      temperature: runtimeConfig.temperature,
      maxTokens: runtimeConfig.maxTokens,
    },
  }
}

export function buildAiAssistantWorkerPayload(runtimeConfig: AiAssistantRuntimeConfig): { modelConfig?: AiAssistantModelConfigPayload } {
  if (runtimeConfig.modelMode === 'deterministic') return {}
  return {
    modelConfig: {
      provider: 'openrouter',
      baseUrl: runtimeConfig.baseUrl,
      model: runtimeConfig.modelName,
      apiKey: runtimeConfig.apiKey,
      temperature: runtimeConfig.temperature,
      maxTokens: runtimeConfig.maxTokens,
    },
  }
}

export interface AiAssistantApproval {
  id: number
  sessionId: number
  runId: number
  toolName: string
  riskLevel: string
  input: Record<string, unknown>
  status: string
  decidedBy?: string | null
  decisionReason?: string
}

export interface AiAssistantApprovalDecision {
  actorId: string
  reason?: string
}

export interface AiAssistantToolManifest {
  name: string
  description: string
  riskLevel: string
  timeoutMs: number
  inputSchema: Record<string, unknown>
  outputSchema: Record<string, unknown>
  readResources: string[]
  writeResources: string[]
  policyRef: string
}

export interface AiAssistantInspectorTask {
  id: string
  runId: number
  planId?: string | null
  planningStrategy?: string
  title: string
  status: string
  phase: string
  currentTool?: string | null
  recognizedNeeds?: string[]
  plannedTools?: string[]
  currentStep?: AiAssistantPlanStep | null
  finalResult?: string
  updatedAt?: string | null
}

export interface AiAssistantInspectorEvent {
  id: number
  sequence: number
  type: string
  status: string
  level: string
  title: string
  summary: string
  createdAt: string
}

export interface AiAssistantContextBudgetLayer {
  name: string
  tokens: number
  sharePercent: number
  selected?: boolean
  source?: string | null
  hash?: string | null
}

export interface AiAssistantContextBudget {
  usage: {
    usedTokens: number
    maxTokens: number
    usagePercent: number
    warningLevel: string
    rawTokens?: number
    rawUsagePercent?: number
  }
  layers: AiAssistantContextBudgetLayer[]
  selectedLayers: AiAssistantContextBudgetLayer[]
  droppedLayers: AiAssistantContextBudgetLayer[]
  dropReasons: Array<{ name: string; reason: string; tokens: number }>
  compactionSnapshot?: {
    rawTokens: number
    summaryTokens: number
    savedPercent: number
    summaryHash?: string
    sourceMessageIds?: number[]
    sourceEventIds?: number[]
    algorithm?: string
  } | null
}

export interface AiAssistantMemoryState {
  sessionSummary?: {
    content: string
    hash?: string
    tokenEstimate?: number
  } | null
  workingMemory: Array<{
    key: string
    value: string
    source?: string
    status?: string
  }>
  instructionMemory?: Array<{
    name: string
    path: string
    hash: string
    tokenEstimate?: number
  }>
}

export interface AiAssistantRunInspector {
  run: AiAssistantRun
  plan?: AiAssistantPlan
  activeTasks: AiAssistantInspectorTask[]
  toolCalls: AiAssistantToolCall[]
  approvalQueue: AiAssistantApproval[]
  approvalHistory: AiAssistantApproval[]
  recentErrors: AiAssistantInspectorEvent[]
  eventTimeline: AiAssistantInspectorEvent[]
  usage: {
    inputTokens: number
    outputTokens: number
    totalTokens: number
    elapsedMs: number
    estimated?: boolean
  }
  memory?: AiAssistantMemoryState
  contextBudget?: AiAssistantContextBudget
}

export interface AiAssistantRunSnapshot {
  run: AiAssistantRun
  events: AiAssistantEvent[]
  streamCursor: {
    lastSequence: number
  }
  inspector: AiAssistantRunInspector
}

export function createAiAssistantSession(payload: { title?: string; context?: Record<string, unknown> } = {}) {
  return post<AiAssistantSession>('/v1/ai-assistant/sessions', payload)
}

export function listAiAssistantSessions() {
  return get<AiAssistantListResult<AiAssistantSession>>('/v1/ai-assistant/sessions')
}

export function clearAiAssistantSessionHistory(sessionId: number) {
  return del<{ sessionId: number; cleared: boolean }>(`/v1/ai-assistant/sessions/${sessionId}/history`)
}

export function deleteAiAssistantSession(sessionId: number) {
  return del<{ sessionId: number; deleted: boolean }>(`/v1/ai-assistant/sessions/${sessionId}`)
}

export function sendAiAssistantMessage(sessionId: number, payload: SendAiAssistantMessagePayload) {
  return post<AiAssistantTurnResult>(`/v1/ai-assistant/sessions/${sessionId}/messages`, payload)
}

export function startAiAssistantMessage(sessionId: number, payload: SendAiAssistantMessagePayload) {
  return post<AiAssistantTurnResult>(`/v1/ai-assistant/sessions/${sessionId}/messages/async`, payload)
}

export function processAiAssistantRunWorker(runId: number, runtimeConfig?: AiAssistantRuntimeConfig) {
  return post<AiAssistantRun & { checkpoint?: Record<string, unknown> }>(
    `/v1/ai-assistant/runs/${runId}/worker/process`,
    runtimeConfig ? buildAiAssistantWorkerPayload(runtimeConfig) : {},
  )
}

export function listAiAssistantRunEvents(runId: number, afterSequence?: number) {
  return get<AiAssistantRunEventList>(
    `/v1/ai-assistant/runs/${runId}/events`,
    afterSequence ? { afterSequence } : undefined,
  )
}

export function listAiAssistantSessionRuns(sessionId: number) {
  return get<AiAssistantListResult<AiAssistantRun>>(`/v1/ai-assistant/sessions/${sessionId}/runs`)
}

export function getAiAssistantRunInspector(runId: number) {
  return get<AiAssistantRunInspector>(`/v1/ai-assistant/runs/${runId}/inspector`)
}

export function getAiAssistantRunSnapshot(runId: number, afterSequence?: number) {
  return get<AiAssistantRunSnapshot>(
    `/v1/ai-assistant/runs/${runId}/snapshot`,
    afterSequence ? { afterSequence } : undefined,
  )
}

export function listAiAssistantApprovals() {
  return get<AiAssistantListResult<AiAssistantApproval>>('/v1/ai-assistant/approvals')
}

export function approveAiAssistantApproval(approvalId: number, payload: AiAssistantApprovalDecision) {
  return post<AiAssistantApproval>(`/v1/ai-assistant/approvals/${approvalId}/approve`, payload)
}

export function denyAiAssistantApproval(approvalId: number, payload: AiAssistantApprovalDecision) {
  return post<AiAssistantApproval>(`/v1/ai-assistant/approvals/${approvalId}/deny`, payload)
}

export function listAiAssistantTools() {
  return get<AiAssistantListResult<AiAssistantToolManifest>>('/v1/ai-assistant/tools')
}
