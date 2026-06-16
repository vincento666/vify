import { get, post, put, del } from '@/utils/request'
import type { PageResult } from '@/api/provider'

export interface AgentListItem {
  id: number
  name: string
  description: string
  modelConfigId: number
  temperature: number
  enabled: number
  toolCount: number
  workflowId?: number | null
  knowledgeBaseId?: number | null
  openingMessage?: string
  suggestedQuestions?: string[]
  createdAt: string
}

export interface AgentVariableDefinition {
  name: string
  type: 'string' | 'number' | 'boolean' | 'json' | string
  defaultValue?: unknown
  required?: boolean
  description?: string
}

export interface AgentToolPolicy {
  enabled?: boolean
  callMode?: string
  argumentPresets?: Record<string, unknown>
  approvalRequired?: boolean
  timeoutMs?: number
  failureBehavior?: string
}

export interface AgentRetrievalSettings {
  topK?: number
  scoreThreshold?: number
  retrievalMode?: 'auto' | 'hybrid' | 'semantic' | 'keyword' | 'faq'
  rerank?: boolean
  citationStyle?: string
}

export interface AgentEvaluationGate {
  enabled?: boolean
  experimentId?: number | null
  requiredPassRate?: number
}

export interface AgentDetail {
  id: number
  name: string
  description: string
  systemPrompt: string
  modelConfigId: number
  temperature: number
  maxTokens: number
  maxContextTurns: number
  enabled: number
  toolIds: number[]
  workflowId?: number | null
  knowledgeBaseId?: number | null
  knowledgeBaseIds?: number[]
  retrievalSettings?: AgentRetrievalSettings
  evaluationGate?: AgentEvaluationGate
  access?: Record<string, unknown>
  sharing?: Record<string, unknown>
  catalog?: Record<string, unknown>
  analytics?: Record<string, unknown>
  openingMessage?: string
  suggestedQuestions?: string[]
  variables?: AgentVariableDefinition[]
  memory?: Record<string, unknown>
  toolPolicies?: Record<string, AgentToolPolicy>
  createdAt: string
  updatedAt: string
}

export interface AgentVersion {
  id: number
  agentId: number
  versionNo: number
  name: string
  snapshot: Record<string, unknown>
  released: boolean
  releasedAt: string | null
  createdAt: string
  updatedAt: string
}

export interface AgentVersionList {
  list: AgentVersion[]
  latestVersionId: number | null
  releasedVersionId: number | null
}

export interface AgentPublishRecord {
  id: number
  agentId: number
  versionId: number
  channelType: string
  status: 'PUBLISHED' | 'UNPUBLISHED' | string
  endpoint: string
  config: Record<string, unknown>
  createdAt: string
  updatedAt: string
}

export interface AgentPublishList {
  list: AgentPublishRecord[]
}

export interface AgentPromptOptimization {
  id: number
  agentId: number
  originalPrompt: string
  instruction: string
  optimizedPrompt: string
  modelConfigId: number
  audit: Record<string, unknown>
  createdAt: string
  updatedAt: string
}

export interface AgentPromptOptimizationList {
  list: AgentPromptOptimization[]
}

export interface AgentPreviewRunDebugDetail {
  previewRunId: number
  agentId: number
  sessionId: number
  status: string
  finishReason: string
  elapsedMs: number
  firstResponseMs: number
  latencyMs: number
  inputChars: number
  outputChars: number
  startedAt: string
  input: Record<string, unknown>
  output: Record<string, unknown>
  toolCalls?: Array<Record<string, unknown>>
  nodes: Array<Record<string, unknown>>
  axisTicks: number[]
  flameLanes: Array<Record<string, unknown>>
}

export interface AgentCreateDTO {
  name: string
  description?: string
  systemPrompt?: string
  modelConfigId: number
  temperature: number
  maxTokens: number
  maxContextTurns: number
  toolIds?: number[]
  workflowId?: number | null
  knowledgeBaseId?: number | null
  knowledgeBaseIds?: number[]
  retrievalSettings?: AgentRetrievalSettings
  evaluationGate?: AgentEvaluationGate
  access?: Record<string, unknown>
  sharing?: Record<string, unknown>
  catalog?: Record<string, unknown>
  analytics?: Record<string, unknown>
  openingMessage?: string
  suggestedQuestions?: string[]
  variables?: AgentVariableDefinition[]
  memory?: Record<string, unknown>
  toolPolicies?: Record<string, AgentToolPolicy>
}

export interface AgentUpdateDTO {
  name: string
  description?: string
  systemPrompt?: string
  modelConfigId: number
  temperature?: number
  maxTokens?: number
  maxContextTurns?: number
  workflowId?: number | null
  knowledgeBaseId?: number | null
  knowledgeBaseIds?: number[]
  retrievalSettings?: AgentRetrievalSettings
  evaluationGate?: AgentEvaluationGate
  access?: Record<string, unknown>
  sharing?: Record<string, unknown>
  catalog?: Record<string, unknown>
  analytics?: Record<string, unknown>
  openingMessage?: string
  suggestedQuestions?: string[]
  variables?: AgentVariableDefinition[]
  memory?: Record<string, unknown>
  toolPolicies?: Record<string, AgentToolPolicy>
}

export interface ModelOption {
  modelConfigId: number
  modelId?: string
  modelName: string
  providerName: string
  providerType: string
  providerBaseUrl?: string
}

export const getAgentList = (params: { page: number; pageSize: number; enabled?: boolean }) =>
  get<PageResult<AgentListItem>>('/v1/agents', params)

export const getAgentDetail = (id: number) =>
  get<AgentDetail>(`/v1/agents/${id}`)

export const createAgent = (data: AgentCreateDTO) =>
  post<AgentDetail>('/v1/agents', data)

export const updateAgent = (id: number, data: AgentUpdateDTO) =>
  put<AgentDetail>(`/v1/agents/${id}`, data)

export const bindAgentTools = (id: number, toolIds: number[]) =>
  put<void>(`/v1/agents/${id}/tools`, { toolIds })

export const deleteAgent = (id: number) =>
  del<void>(`/v1/agents/${id}`)

export const getAgentVersions = (id: number) =>
  get<AgentVersionList>(`/v1/agents/${id}/versions`)

export const createAgentVersion = (id: number, name = '') =>
  post<AgentVersion>(`/v1/agents/${id}/versions`, { name })

export const releaseAgentVersion = (agentId: number, versionId: number) =>
  put<AgentVersion>(`/v1/agents/${agentId}/versions/${versionId}/release`, {})

export const getAgentPublishes = (id: number) =>
  get<AgentPublishList>(`/v1/agents/${id}/publishes`)

export const publishAgentVersion = (agentId: number, versionId: number, channelType = 'API') =>
  post<AgentPublishRecord>(`/v1/agents/${agentId}/publishes`, { versionId, channelType })

export const unpublishAgentRecord = (agentId: number, publishId: number) =>
  put<AgentPublishRecord>(`/v1/agents/${agentId}/publishes/${publishId}/unpublish`, {})

export const optimizeAgentPrompt = (agentId: number, instruction: string) =>
  post<AgentPromptOptimization>(`/v1/agents/${agentId}/prompt-optimizations`, { instruction })

export const getAgentPromptOptimizations = (agentId: number) =>
  get<AgentPromptOptimizationList>(`/v1/agents/${agentId}/prompt-optimizations`)

export const getAgentPreviewRunDebug = (agentId: number, previewRunId: number) =>
  get<AgentPreviewRunDebugDetail>(`/v1/agents/${agentId}/preview-runs/${previewRunId}/debug`)

/** 从 provider 列表中提取所有已启用的模型，供 Agent 表单选择 */
export const getModelOptions = async (params?: { includeMock?: boolean }): Promise<ModelOption[]> => {
  const { getProviderList } = await import('@/api/provider')
  const options: ModelOption[] = []
  for (let page = 1; page <= 20; page += 1) {
    const res = await getProviderList({ page, pageSize: 100 })
    for (const provider of res.list) {
      if (!provider.enabled) continue
      if (!params?.includeMock && String(provider.baseUrl || '').startsWith('mock://')) continue
      for (const model of provider.models ?? []) {
        if (!model.enabled) continue
        options.push({
          modelConfigId: model.id,
          modelId: model.modelId,
          modelName: model.name,
          providerName: provider.name,
          providerType: provider.type,
          providerBaseUrl: provider.baseUrl,
        })
      }
    }
    if (res.list.length === 0 || page * 100 >= res.total) break
  }
  return options
}
