import { get, post, put } from '@/utils/request'

export interface RuntimeLabSession {
  id: number
  status?: string
  activeTaskId?: number | null
  version?: number
  createdAt?: string | null
  updatedAt?: string | null
}

export interface RuntimeLabTask {
  id: number
  sessionId?: number
  sopId: string
  status: string
  currentStep?: string | null
  checkpointId?: string | null
  parentTaskId?: number | null
  resumeSummary?: string | null
  businessRefs?: Record<string, unknown>
  suspendedAt?: string | null
  completedAt?: string | null
  createdAt?: string | null
  updatedAt?: string | null
}

export interface RuntimeLabEvent {
  id: number
  sessionId: number
  sequence: number
  eventType: string
  payload: Record<string, unknown>
  createdAt: string | null
}

export interface RuntimeLabRouteDecision {
  action: string
  reason?: string | null
  targetSopId?: string | null
  activeTaskId?: number | null
  matchedKeyword?: string | null
  clarificationQuestion?: string | null
  candidates?: unknown[]
  candidateSources?: string[]
  policyGate?: Record<string, unknown> | null
  classifierRequest?: Record<string, unknown> | null
  classifierResult?: Record<string, unknown> | null
  finalDecision?: Record<string, unknown> | null
  handoff?: Record<string, unknown> | null
  faqAnswer?: Record<string, unknown> | null
  ragAnswer?: Record<string, unknown> | null
  agentAnswer?: Record<string, unknown> | null
}

export interface RuntimeLabUsage {
  inputTokens: number
  outputTokens: number
  totalTokens: number
  estimated?: boolean
}

export interface RuntimeLabResumeOffer {
  taskId?: number
  sopId?: string
  prompt?: string
  [key: string]: unknown
}

export interface RuntimeLabTurn {
  reply: string
  routeDecision: RuntimeLabRouteDecision
  activeTask: RuntimeLabTask | null
  suspendedTasks: RuntimeLabTask[]
  resumeOffer: RuntimeLabResumeOffer | null
  events?: RuntimeLabEvent[]
}

export interface RuntimeLabMessagePayload {
  message: string
  idempotencyKey?: string
  enabledSopIds?: string[]
  routeSettings?: RuntimeLabRouteSettingsPayload
}

export interface RuntimeLabListResult<T> {
  list: T[]
  total: number
}

export interface RuntimeLabSopBinding {
  sopId: string
  chatflowId: number
  chatflowName: string
  exists: boolean
  canvasPath: string
}

export interface RuntimeLabArbitratorConfig {
  mode: string
  model: string
  fallbackModel?: string
  baseUrl: string
  apiKeyConfigured: boolean
  available: boolean
}

export interface RuntimeLabPolicyProfile {
  source: string
  profileId?: number | null
  profileVersion?: number | null
}

export interface RuntimeLabThresholdConfig {
  strongAcceptThreshold?: number
  classifierMinConfidence?: number
  candidateTopK?: number
  candidateSourceWeights?: Record<string, number>
  llmArbitrationRequiredForNonHardStop?: boolean
  faqKeywordMinScore?: number
  faqKeywordMinMargin?: number
  faqSemanticMinScore?: number
  faqSemanticMinMargin?: number
  ragMinScore?: number
  ragLexicalAcceptThreshold?: number
}

export interface RuntimeLabFaqConfig {
  knowledgeBaseIds: number[]
  exactEnabled?: boolean
  semanticEnabled?: boolean
  topK?: number
  rerank?: boolean
}

export interface RuntimeLabRagConfig {
  enabled?: boolean
  knowledgeBaseIds: number[]
  retrievalMode?: string
  topK?: number
  rerank?: boolean
}

export interface RuntimeLabHandoffConfig {
  enabled?: boolean
  queue?: string
}

export interface RuntimeLabFallbackAgentConfig {
  enabled: boolean
  type: string
  agentId: number | null
  agentName: string
  available: boolean
}

export interface RuntimeLabFallbackAgentOption {
  id: number
  name: string
  description: string
  enabled: boolean
}

export interface RuntimeLabConfig {
  policyProfile?: RuntimeLabPolicyProfile
  sopBindings: RuntimeLabSopBinding[]
  arbitrator: RuntimeLabArbitratorConfig
  thresholds?: RuntimeLabThresholdConfig
  faq?: RuntimeLabFaqConfig
  rag?: RuntimeLabRagConfig
  handoff?: RuntimeLabHandoffConfig
  fallbackAgent?: RuntimeLabFallbackAgentConfig
  fallbackAgentOptions?: RuntimeLabFallbackAgentOption[]
}

export interface RuntimeLabRouteSettingsPayload {
  arbitrator?: {
    mode?: string
    model?: string
    fallbackModel?: string
    modelConfigId?: number | null
    fallbackModelConfigId?: number | null
    temporaryModel?: RuntimeLabTemporaryModelPayload
    temporaryFallbackModel?: RuntimeLabTemporaryModelPayload
  }
  thresholds?: RuntimeLabThresholdConfig
}

export interface RuntimeLabTemporaryModelPayload {
  enabled?: boolean
  model?: string
  baseUrl?: string
  apiKey?: string
  temperature?: number
  maxTokens?: number
  topP?: number
}

export interface RuntimeLabTemporaryModelTestResult {
  ok: boolean
  model: string
  elapsedMs: number
  usage?: RuntimeLabUsage
  replyPreview?: string
  error?: string
}

export interface RuntimeLabFallbackAgentUpdateResult extends Omit<RuntimeLabConfig, 'fallbackAgent'> {
  fallbackAgent: RuntimeLabFallbackAgentConfig
}

export interface RuntimeLabChatflowTrace {
  tasks: RuntimeLabChatflowTaskTrace[]
  total: number
}

export interface RuntimeLabChatflowTaskTrace {
  taskId: number
  sopId: string
  status: string
  // Optional since slice 213.3.5f: sourced from the durable runtime-v2 waiting
  // checkpoint (pending_node_key) and absent when no run is waiting.
  currentStep?: string
  chatflow: RuntimeLabTraceChatflow
  nodes: RuntimeLabTraceNode[]
  edges: RuntimeLabTraceEdge[]
  events: RuntimeLabTraceEvent[]
  variables: RuntimeLabTraceVariables
}

export interface RuntimeLabTraceChatflow {
  chatflowId: number | null
  chatflowName: string
  exists: boolean
  runId: number | null
  eventId: number | null
  checkpointId: number | null
  sessionId: string
  canvasPath: string
  debugPath: string
}

export interface RuntimeLabTraceNode {
  nodeKey: string
  nodeType: string
  name: string
  status: string
  current: boolean
  elapsedMs: number
  inputs: Record<string, unknown>
  outputs: Record<string, unknown>
  usage: RuntimeLabUsage
  error: string
}

export interface RuntimeLabTraceEdge {
  sourceNodeKey: string
  targetNodeKey: string
  condition: string | null
}

export interface RuntimeLabTraceEvent {
  id: number
  type: string
  runId: number
  sequence: number
  nodeKey: string
  payload: Record<string, unknown>
  checkpointId: number | null
  createdAt: string | null
}

export interface RuntimeLabTraceVariables {
  // businessRefs / collected are both the aggregator projection (chatflow
  // conversation scope + regex-derived refs) since slice 213.3.5f; the legacy
  // checkpoint.collected / task.business_refs reads were banned in 213.3.5e.
  businessRefs: Record<string, unknown>
  collected: Record<string, unknown>
  scoped: Record<string, unknown>
  session: Record<string, unknown>
}

export const createRuntimeLabSession = () =>
  post<RuntimeLabSession>('/v1/runtime-lab/sessions')

export const postRuntimeLabMessage = (
  sessionId: number,
  payload: RuntimeLabMessagePayload,
) => post<RuntimeLabTurn>(`/v1/runtime-lab/sessions/${sessionId}/messages`, payload)

export const listRuntimeLabTasks = (sessionId: number) =>
  get<RuntimeLabListResult<RuntimeLabTask>>(`/v1/runtime-lab/sessions/${sessionId}/tasks`)

export const listRuntimeLabEvents = (sessionId: number) =>
  get<RuntimeLabListResult<RuntimeLabEvent>>(`/v1/runtime-lab/sessions/${sessionId}/events`)

export const getRuntimeLabConfig = () =>
  get<RuntimeLabConfig>('/v1/runtime-lab/config')

export const updateRuntimeLabFallbackAgent = (payload: { enabled: boolean; agentId?: number | null }) =>
  put<RuntimeLabFallbackAgentUpdateResult>('/v1/runtime-lab/fallback-agent', payload)

export const getRuntimeLabChatflowTrace = (sessionId: number) =>
  get<RuntimeLabChatflowTrace>(`/v1/runtime-lab/sessions/${sessionId}/chatflow-trace`)

export const testRuntimeLabTemporaryModel = (payload: RuntimeLabTemporaryModelPayload) =>
  post<RuntimeLabTemporaryModelTestResult>('/v1/runtime-lab/route-model/connectivity', payload)
