import { get, post } from '@/utils/request'

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

export interface AiAssistantTurnResult {
  runId: number
  sessionId: number
  status: string
  replayed: boolean
  finalAnswer: string
  toolCalls: AiAssistantToolCall[]
  approvalRequired?: boolean
  approvalId?: number | null
  sandboxDenied?: boolean
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
  approvalMode?: string
  toolName?: string
  toolInput?: Record<string, unknown>
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
  title: string
  status: string
  phase: string
  currentTool?: string | null
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

export interface AiAssistantRunInspector {
  run: AiAssistantRun
  activeTasks: AiAssistantInspectorTask[]
  toolCalls: AiAssistantToolCall[]
  approvalQueue: AiAssistantApproval[]
  recentErrors: AiAssistantInspectorEvent[]
  eventTimeline: AiAssistantInspectorEvent[]
  usage: {
    inputTokens: number
    outputTokens: number
    totalTokens: number
    elapsedMs: number
  }
}

export function createAiAssistantSession(payload: { title?: string; context?: Record<string, unknown> } = {}) {
  return post<AiAssistantSession>('/v1/ai-assistant/sessions', payload)
}

export function listAiAssistantSessions() {
  return get<AiAssistantListResult<AiAssistantSession>>('/v1/ai-assistant/sessions')
}

export function sendAiAssistantMessage(sessionId: number, payload: SendAiAssistantMessagePayload) {
  return post<AiAssistantTurnResult>(`/v1/ai-assistant/sessions/${sessionId}/messages`, payload)
}

export function listAiAssistantRunEvents(runId: number) {
  return get<AiAssistantRunEventList>(`/v1/ai-assistant/runs/${runId}/events`)
}

export function listAiAssistantSessionRuns(sessionId: number) {
  return get<AiAssistantListResult<AiAssistantRun>>(`/v1/ai-assistant/sessions/${sessionId}/runs`)
}

export function getAiAssistantRunInspector(runId: number) {
  return get<AiAssistantRunInspector>(`/v1/ai-assistant/runs/${runId}/inspector`)
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
