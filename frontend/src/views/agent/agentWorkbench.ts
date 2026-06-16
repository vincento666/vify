import type {
  AgentCreateDTO,
  AgentDetail,
  AgentEvaluationGate,
  AgentRetrievalSettings,
  AgentToolPolicy,
  AgentUpdateDTO,
  AgentVariableDefinition,
  AgentVersionList,
  ModelOption,
} from '@/api/agent'

export interface AgentWorkbenchForm {
  name: string
  description: string
  systemPrompt: string
  modelConfigId: number | null
  temperature: number
  maxTokens: number
  maxContextTurns: number
  openingMessage: string
  suggestedQuestions: string[]
  variables: AgentVariableDefinition[]
  memory: Record<string, unknown>
  toolPolicies: Record<string, AgentToolPolicy>
  toolIds: number[]
  knowledgeBaseId: number | null
  knowledgeBaseIds: number[]
  retrievalSettings: Required<AgentRetrievalSettings>
  evaluationGate: Required<AgentEvaluationGate>
  access: Record<string, unknown>
  sharing: Record<string, unknown>
  catalog: Record<string, unknown>
  analytics: Record<string, unknown>
  workflowId: number | null
}

export interface AgentWorkbenchValidationError {
  field: keyof AgentWorkbenchForm
  message: string
}

export interface ModelOptionGroup {
  providerName: string
  models: ModelOption[]
}

export interface AgentCapabilitySummary {
  toolCount: number
  hasKnowledgeBase: boolean
  hasWorkflow: boolean
  summary: string
}

export type AgentRuntimeMode = 'workflow' | 'rag' | 'direct-tools' | 'direct'

export interface AgentRuntimeSummary {
  mode: AgentRuntimeMode
  badge: string
  summary: string
  warnings: string[]
}

export interface PreviewGateInput {
  isCreateMode: boolean
  dirty: boolean
  streaming: boolean
}

export interface PreviewGate {
  canSend: boolean
  reason: string
}

export interface WorkbenchReadinessInput {
  modelCount: number
  mcpServerCount: number
  knowledgeBaseCount: number
  workflowCount: number
}

export interface PreviewWelcomeState {
  openingMessage: string
  suggestedQuestions: string[]
}

export interface PreviewTargetOption {
  value: string
  label: string
  description: string
}

export function defaultAgentWorkbenchForm(): AgentWorkbenchForm {
  return {
    name: '',
    description: '',
    systemPrompt: '',
    modelConfigId: null,
    temperature: 0.7,
    maxTokens: 2048,
    maxContextTurns: 10,
    openingMessage: '',
    suggestedQuestions: [],
    variables: [],
    memory: {},
    toolPolicies: {},
    toolIds: [],
    knowledgeBaseId: null,
    knowledgeBaseIds: [],
    retrievalSettings: { topK: 3, scoreThreshold: 0, retrievalMode: 'auto', rerank: false, citationStyle: 'numbered' },
    evaluationGate: { enabled: false, experimentId: null, requiredPassRate: 1 },
    access: { mode: 'PRIVATE', owners: [], readonly: false },
    sharing: { enabled: false, publicToken: '' },
    catalog: { visible: false, category: '' },
    analytics: { usage: 0, latencyMs: 0, errors: 0 },
    workflowId: null,
  }
}

export function agentDetailToForm(detail: AgentDetail): AgentWorkbenchForm {
  return {
    name: detail.name,
    description: detail.description ?? '',
    systemPrompt: detail.systemPrompt ?? '',
    modelConfigId: detail.modelConfigId,
    temperature: detail.temperature,
    maxTokens: detail.maxTokens,
    maxContextTurns: detail.maxContextTurns,
    openingMessage: detail.openingMessage ?? '',
    suggestedQuestions: normalizeSuggestedQuestions(detail.suggestedQuestions ?? []),
    variables: normalizeVariableDefinitions(detail.variables ?? []),
    memory: normalizeMemory(detail.memory ?? {}),
    toolPolicies: normalizeToolPolicies(detail.toolPolicies ?? {}),
    toolIds: detail.toolIds ?? [],
    knowledgeBaseId: detail.knowledgeBaseId ?? null,
    knowledgeBaseIds: normalizeKnowledgeBaseIds(detail.knowledgeBaseId ?? null, detail.knowledgeBaseIds ?? []),
    retrievalSettings: normalizeRetrievalSettings(detail.retrievalSettings ?? {}),
    evaluationGate: normalizeEvaluationGate(detail.evaluationGate ?? {}),
    access: detail.access ?? { mode: 'PRIVATE', owners: [], readonly: false },
    sharing: detail.sharing ?? { enabled: false, publicToken: '' },
    catalog: detail.catalog ?? { visible: false, category: '' },
    analytics: detail.analytics ?? { usage: 0, latencyMs: 0, errors: 0 },
    workflowId: detail.workflowId ?? null,
  }
}

export function formToAgentCreatePayload(form: AgentWorkbenchForm): AgentCreateDTO {
  return {
    name: form.name.trim(),
    description: form.description,
    systemPrompt: form.systemPrompt,
    modelConfigId: form.modelConfigId!,
    temperature: form.temperature,
    maxTokens: form.maxTokens,
    maxContextTurns: form.maxContextTurns,
    openingMessage: form.openingMessage.trim(),
    suggestedQuestions: normalizeSuggestedQuestions(form.suggestedQuestions),
    variables: normalizeVariableDefinitions(form.variables),
    memory: normalizeMemory(form.memory),
    toolPolicies: normalizeToolPolicies(form.toolPolicies),
    toolIds: [...form.toolIds],
    knowledgeBaseId: form.knowledgeBaseId,
    knowledgeBaseIds: normalizeKnowledgeBaseIds(form.knowledgeBaseId, form.knowledgeBaseIds),
    retrievalSettings: normalizeRetrievalSettings(form.retrievalSettings),
    evaluationGate: normalizeEvaluationGate(form.evaluationGate),
    access: form.access,
    sharing: form.sharing,
    catalog: form.catalog,
    analytics: form.analytics,
    workflowId: form.workflowId,
  }
}

export function formToAgentUpdatePayload(form: AgentWorkbenchForm): AgentUpdateDTO {
  return {
    name: form.name.trim(),
    description: form.description,
    systemPrompt: form.systemPrompt,
    modelConfigId: form.modelConfigId!,
    temperature: form.temperature,
    maxTokens: form.maxTokens,
    maxContextTurns: form.maxContextTurns,
    openingMessage: form.openingMessage.trim(),
    suggestedQuestions: normalizeSuggestedQuestions(form.suggestedQuestions),
    variables: normalizeVariableDefinitions(form.variables),
    memory: normalizeMemory(form.memory),
    toolPolicies: normalizeToolPolicies(form.toolPolicies),
    knowledgeBaseId: form.knowledgeBaseId,
    knowledgeBaseIds: normalizeKnowledgeBaseIds(form.knowledgeBaseId, form.knowledgeBaseIds),
    retrievalSettings: normalizeRetrievalSettings(form.retrievalSettings),
    evaluationGate: normalizeEvaluationGate(form.evaluationGate),
    access: form.access,
    sharing: form.sharing,
    catalog: form.catalog,
    analytics: form.analytics,
    workflowId: form.workflowId,
  }
}

export function validateAgentWorkbenchForm(form: AgentWorkbenchForm): AgentWorkbenchValidationError[] {
  const errors: AgentWorkbenchValidationError[] = []
  if (!form.name.trim()) {
    errors.push({ field: 'name', message: '请输入 Agent 名称' })
  }
  if (!form.modelConfigId) {
    errors.push({ field: 'modelConfigId', message: '请选择模型' })
  }
  if (form.temperature < 0 || form.temperature > 1) {
    errors.push({ field: 'temperature', message: 'Temperature 必须在 0 到 1 之间' })
  }
  if (!Number.isFinite(form.maxTokens) || form.maxTokens < 1) {
    errors.push({ field: 'maxTokens', message: '最大输出 Token 必须大于 0' })
  }
  if (!Number.isFinite(form.maxContextTurns) || form.maxContextTurns < 1) {
    errors.push({ field: 'maxContextTurns', message: '上下文轮数必须大于 0' })
  }
  for (const variable of form.variables) {
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(String(variable.name || '').trim())) {
      errors.push({ field: 'variables', message: '变量名只能使用字母、数字和下划线，且不能以数字开头' })
      break
    }
  }
  return errors
}

export function isAgentFormDirty(current: AgentWorkbenchForm, baseline: AgentWorkbenchForm): boolean {
  return JSON.stringify(normalizeForCompare(current)) !== JSON.stringify(normalizeForCompare(baseline))
}

export function cloneAgentForm(form: AgentWorkbenchForm): AgentWorkbenchForm {
  return JSON.parse(JSON.stringify(form)) as AgentWorkbenchForm
}

export function groupModelOptions(options: ModelOption[]): ModelOptionGroup[] {
  const map = new Map<string, ModelOptionGroup>()
  for (const option of options) {
    if (!map.has(option.providerName)) {
      map.set(option.providerName, { providerName: option.providerName, models: [] })
    }
    map.get(option.providerName)!.models.push(option)
  }
  return Array.from(map.values())
}

export function summarizeAgentCapabilities(form: AgentWorkbenchForm): AgentCapabilitySummary {
  const parts: string[] = []
  if (form.toolIds.length > 0) parts.push(`${form.toolIds.length} 个 MCP Server`)
  if (form.knowledgeBaseId) parts.push('知识库')
  if (form.workflowId) parts.push('工作流')
  return {
    toolCount: form.toolIds.length,
    hasKnowledgeBase: Boolean(form.knowledgeBaseId),
    hasWorkflow: Boolean(form.workflowId),
    summary: parts.length ? parts.join(' / ') : '未绑定能力',
  }
}

export function resolveAgentRuntimeMode(form: AgentWorkbenchForm): AgentRuntimeSummary {
  if (form.workflowId) {
    const warnings: string[] = []
    if (form.knowledgeBaseId) {
      warnings.push('已绑定知识库，但工作流优先，RAG 不会直接参与本次 Agent 聊天路径。')
    }
    if (form.toolIds.length > 0) {
      warnings.push('已绑定 MCP 工具，但工作流模式优先，工具不会进入模型工具调用路径。')
    }
    return {
      mode: 'workflow',
      badge: '工作流',
      summary: '工作流优先运行并决定回复路径',
      warnings,
    }
  }

  if (form.knowledgeBaseId) {
    const warnings = form.toolIds.length > 0
      ? ['已绑定 MCP 工具，但 RAG 模式优先，工具不会进入模型工具调用路径。']
      : []
    return {
      mode: 'rag',
      badge: 'RAG',
      summary: '知识库会在模型回答前被检索',
      warnings,
    }
  }

  if (form.toolIds.length > 0) {
    return {
      mode: 'direct-tools',
      badge: 'LLM + 工具',
      summary: '使用当前真实模型回复，并允许调用已绑定 MCP 工具',
      warnings: [],
    }
  }

  return {
    mode: 'direct',
    badge: 'LLM',
    summary: '使用当前真实模型回复，不经过工作流或知识库',
    warnings: [],
  }
}

export function resolvePreviewGate(input: PreviewGateInput): PreviewGate {
  if (input.isCreateMode) {
    return { canSend: false, reason: '请先保存 Agent 后再预览。' }
  }
  if (input.dirty) {
    return { canSend: false, reason: '当前配置有未保存更改，请保存后再预览。' }
  }
  if (input.streaming) {
    return { canSend: false, reason: '正在生成回复。' }
  }
  return { canSend: true, reason: '' }
}

export function buildWorkbenchReadinessMessages(input: WorkbenchReadinessInput): string[] {
  const messages: string[] = []
  if (input.modelCount === 0) messages.push('暂无可用模型，请先在模型提供商中启用模型。')
  if (input.mcpServerCount === 0) messages.push('暂无启用的 MCP Server，可先到 MCP 管理中添加。')
  if (input.knowledgeBaseCount === 0) messages.push('暂无启用知识库，可先创建知识库。')
  if (input.workflowCount === 0) messages.push('暂无工作流，可先创建 Workflow。')
  return messages
}

export function buildPreviewWelcomeState(form: AgentWorkbenchForm): PreviewWelcomeState {
  return {
    openingMessage: form.openingMessage.trim(),
    suggestedQuestions: normalizeSuggestedQuestions(form.suggestedQuestions),
  }
}

export function buildPreviewTargetOptions(versions: AgentVersionList | null): PreviewTargetOption[] {
  const options: PreviewTargetOption[] = [
    { value: 'draft', label: 'Draft 当前草稿', description: '使用当前已保存 Agent 配置' },
  ]
  if (!versions) return options

  const latest = versions.list.find((version) => version.id === versions.latestVersionId)
  if (latest) {
    options.push({
      value: `latest:${latest.id}`,
      label: `Latest v${latest.versionNo} ${latest.name}`.trim(),
      description: '最近保存的不可变版本',
    })
  }

  const released = versions.list.find((version) => version.id === versions.releasedVersionId)
  if (released) {
    options.push({
      value: `released:${released.id}`,
      label: `Released v${released.versionNo} ${released.name}`.trim(),
      description: '当前发布版本',
    })
  }
  return options
}

export function formatWorkbenchBackendError(error: unknown): string {
  if (typeof error === 'object' && error && 'message' in error) {
    const message = String((error as { message?: unknown }).message || '').trim()
    if (message) return message
  }
  return '保存 Agent 失败'
}

function normalizeForCompare(form: AgentWorkbenchForm) {
  return {
    ...form,
    name: form.name.trim(),
    openingMessage: form.openingMessage.trim(),
    suggestedQuestions: normalizeSuggestedQuestions(form.suggestedQuestions),
    variables: normalizeVariableDefinitions(form.variables),
    memory: normalizeMemory(form.memory),
    toolPolicies: normalizeToolPolicies(form.toolPolicies),
    knowledgeBaseIds: normalizeKnowledgeBaseIds(form.knowledgeBaseId, form.knowledgeBaseIds),
    retrievalSettings: normalizeRetrievalSettings(form.retrievalSettings),
    evaluationGate: normalizeEvaluationGate(form.evaluationGate),
    toolIds: [...form.toolIds].sort((a, b) => a - b),
  }
}

function normalizeSuggestedQuestions(questions: string[]): string[] {
  const normalized: string[] = []
  const seen = new Set<string>()
  for (const question of questions) {
    const value = String(question || '').trim()
    if (!value || seen.has(value)) continue
    seen.add(value)
    normalized.push(value)
  }
  return normalized
}

export function buildPreviewVariableOverrides(values: Record<string, unknown>): Record<string, unknown> {
  const overrides: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(values)) {
    if (typeof value === 'string') {
      const trimmed = value.trim()
      if (trimmed) overrides[key] = trimmed
      continue
    }
    if (value !== null && value !== undefined && value !== '') {
      overrides[key] = value
    }
  }
  return overrides
}

export function normalizeVariableDefinitions(variables: AgentVariableDefinition[]): AgentVariableDefinition[] {
  const normalized: AgentVariableDefinition[] = []
  const seen = new Set<string>()
  for (const variable of variables) {
    const name = String(variable.name || '').trim()
    if (!name || seen.has(name)) continue
    seen.add(name)
    normalized.push({
      name,
      type: String(variable.type || 'string').toLowerCase(),
      defaultValue: variable.defaultValue ?? '',
      required: Boolean(variable.required),
      description: String(variable.description || '').trim(),
    })
  }
  return normalized
}

export function normalizeMemory(memory: Record<string, unknown>): Record<string, unknown> {
  const normalized: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(memory || {})) {
    const normalizedKey = key.trim()
    if (!normalizedKey) continue
    normalized[normalizedKey] = value
  }
  return normalized
}

export function normalizeToolPolicies(policies: Record<string, AgentToolPolicy>): Record<string, AgentToolPolicy> {
  const normalized: Record<string, AgentToolPolicy> = {}
  for (const [name, policy] of Object.entries(policies || {})) {
    const toolName = name.trim()
    if (!toolName) continue
    normalized[toolName] = {
      enabled: policy.enabled !== false,
      callMode: policy.callMode || 'auto',
      argumentPresets: policy.argumentPresets || {},
      approvalRequired: Boolean(policy.approvalRequired),
      timeoutMs: Math.max(1, Number(policy.timeoutMs || 30000)),
      failureBehavior: policy.failureBehavior || 'return_error',
    }
  }
  return normalized
}

export function normalizeKnowledgeBaseIds(primaryId: number | null, ids: number[]): number[] {
  const normalized: number[] = []
  for (const rawId of [primaryId, ...(ids || [])]) {
    const id = Number(rawId || 0)
    if (!id || normalized.includes(id)) continue
    normalized.push(id)
  }
  return normalized
}

export function normalizeRetrievalSettings(settings: AgentRetrievalSettings): Required<AgentRetrievalSettings> {
  const rawMode = String(settings.retrievalMode || 'auto')
  const retrievalMode = ['auto', 'hybrid', 'semantic', 'keyword', 'faq'].includes(rawMode) ? rawMode : 'auto'
  return {
    topK: Math.min(Math.max(Number(settings.topK || 3), 1), 20),
    scoreThreshold: Math.min(Math.max(Number(settings.scoreThreshold || 0), 0), 1),
    retrievalMode: retrievalMode as Required<AgentRetrievalSettings>['retrievalMode'],
    rerank: Boolean(settings.rerank),
    citationStyle: settings.citationStyle || 'numbered',
  }
}

export function resolveFlowCanvasRoute(flow: { id: number; flowType?: string }) {
  return String(flow.flowType || '').toUpperCase() === 'CHATFLOW'
    ? { name: 'HifyChatflowsCanvas', params: { id: flow.id } }
    : { name: 'HifyWorkflowsCanvas', params: { id: flow.id } }
}

export function resolveFlowCanvasPath(flow: { id: number; flowType?: string }): string {
  return String(flow.flowType || '').toUpperCase() === 'CHATFLOW'
    ? `/chatflows/${flow.id}/canvas`
    : `/workflows/${flow.id}/canvas`
}

export function normalizeEvaluationGate(gate: AgentEvaluationGate): Required<AgentEvaluationGate> {
  return {
    enabled: Boolean(gate.enabled),
    experimentId: gate.experimentId ?? null,
    requiredPassRate: Math.min(Math.max(Number(gate.requiredPassRate || 1), 0), 1),
  }
}
