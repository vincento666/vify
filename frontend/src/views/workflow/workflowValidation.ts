import type { WorkflowCanvasGraph } from './flowGraph'

export interface WorkflowValidationResult {
  valid: boolean
  errors: string[]
}

export function mergeWorkflowValidationErrors(...groups: string[][]) {
  const seen = new Set<string>()
  const errors: string[] = []
  for (const group of groups) {
    for (const error of group) {
      if (seen.has(error)) continue
      seen.add(error)
      errors.push(error)
    }
  }
  return errors
}

function hasPathToEnd(graph: WorkflowCanvasGraph) {
  const adjacency = new Map<string, string[]>()
  for (const edge of graph.edges) {
    const next = adjacency.get(edge.sourceNodeKey) || []
    next.push(edge.targetNodeKey)
    adjacency.set(edge.sourceNodeKey, next)
  }

  const seen = new Set<string>()
  const stack = ['start']
  while (stack.length > 0) {
    const current = stack.pop()!
    if (current === 'end') return true
    if (seen.has(current)) continue
    seen.add(current)
    stack.push(...(adjacency.get(current) || []))
  }
  return false
}

function normalizeBranchKey(value: unknown) {
  const text = String(value ?? '').trim()
  return text.length > 0 ? text : null
}

function outgoingConditions(graph: WorkflowCanvasGraph, nodeKey: string) {
  return new Set(
    graph.edges
      .filter((edge) => edge.sourceNodeKey === nodeKey)
      .map((edge) => normalizeBranchKey(edge.condition)),
  )
}

function branchKeysFromConfig(config: Record<string, any>, key: 'conditionBranches' | 'branches') {
  const raw = config[key]
  if (!Array.isArray(raw)) return []
  const keys = raw
    .map((branch, index) => normalizeBranchKey(branch?.key ?? branch?.id ?? `branch_${index + 1}`))
    .filter((branchKey): branchKey is string => Boolean(branchKey))
  return [...new Set(keys)]
}

function conditionBranchKeys(config: Record<string, any>) {
  const explicitBranches = branchKeysFromConfig(config, 'conditionBranches')
  if (explicitBranches.length > 0) return explicitBranches
  return branchKeysFromConfig(config, 'branches')
}

function intentBranchKeys(config: Record<string, any>) {
  const defaultKey = normalizeBranchKey(config.defaultIntent) || 'default'
  const intents = Array.isArray(config.intents) ? config.intents : []
  const keys = intents
    .map((intent, index) => normalizeBranchKey(intent?.key ?? intent?.id ?? `intent_${index + 1}`))
    .filter((intentKey): intentKey is string => Boolean(intentKey) && intentKey !== defaultKey)
  return [...new Set(keys)]
}

const ERROR_BEHAVIORS = new Set(['fail', 'continue', 'branch'])
const SENSITIVE_HEADER_NAMES = new Set([
  'authorization',
  'cookie',
  'proxy-authorization',
  'x-api-key',
  'api-key',
  'x-token',
  'token',
  'secret',
])

function hasExplicitValue(value: unknown) {
  return String(value ?? '').trim().length > 0
}

function hasPositiveNumber(value: unknown) {
  return Number(value) > 0
}

function hasNonNegativeNumber(value: unknown) {
  return value !== undefined && value !== null && Number(value) >= 0
}

function hasOutputSchema(config: Record<string, any>) {
  if (Array.isArray(config.outputParameters) && config.outputParameters.length > 0) return true
  const schema = config.outputSchema
  if (schema && typeof schema === 'object' && !Array.isArray(schema)) return Object.keys(schema).length > 0
  return typeof schema === 'string' && schema.trim().length > 0 && schema.trim() !== '{}'
}

function configuredTimeoutMs(config: Record<string, any>) {
  return hasPositiveNumber(config.timeoutMs) ? Number(config.timeoutMs) : Number(config.timeout || 0) * 1000
}

function headerRows(headers: unknown): Array<{ name: string }> {
  const raw = typeof headers === 'string' && headers.trim().length > 0
    ? parseJson(headers, [])
    : headers
  if (Array.isArray(raw)) {
    return raw
      .map((header) => ({ name: String(header?.name || header?.key || '').trim() }))
      .filter((header) => header.name.length > 0)
  }
  if (raw && typeof raw === 'object') {
    return Object.keys(raw).map((name) => ({ name }))
  }
  return []
}

function parseJson(value: string, fallback: unknown) {
  try {
    return JSON.parse(value)
  } catch {
    return fallback
  }
}

function sensitiveHeaderSet(config: Record<string, any>) {
  const raw = config.sensitiveHeaders
  if (Array.isArray(raw)) return new Set(raw.map((item) => String(item).trim().toLowerCase()).filter(Boolean))
  if (typeof raw === 'string') {
    const parsed = parseJson(raw, null)
    if (Array.isArray(parsed)) return new Set(parsed.map((item) => String(item).trim().toLowerCase()).filter(Boolean))
    return new Set(raw.split(',').map((item) => item.trim().toLowerCase()).filter(Boolean))
  }
  return new Set<string>()
}

function validateApiGovernance(nodeKey: string, config: Record<string, any>, errors: string[]) {
  if (!hasExplicitValue(config.authMode)) errors.push(`API 节点 ${nodeKey} 需要配置认证策略`)
  if (!hasPositiveNumber(configuredTimeoutMs(config))) errors.push(`API 节点 ${nodeKey} 需要配置超时毫秒`)
  if (!hasNonNegativeNumber(config.retryCount)) errors.push(`API 节点 ${nodeKey} 需要配置重试次数`)
  if (!ERROR_BEHAVIORS.has(String(config.errorBehavior || '').trim())) errors.push(`API 节点 ${nodeKey} 需要配置错误行为`)
  if (!hasOutputSchema(config)) errors.push(`API 节点 ${nodeKey} 需要配置输出 Schema`)

  const redactedHeaders = sensitiveHeaderSet(config)
  for (const header of headerRows(config.headers)) {
    const normalized = header.name.toLowerCase()
    if (SENSITIVE_HEADER_NAMES.has(normalized) && !redactedHeaders.has(normalized)) {
      errors.push(`API 节点 ${nodeKey} 的敏感请求头 ${header.name} 需要加入脱敏列表`)
    }
  }
}

function validateToolGovernance(nodeKey: string, config: Record<string, any>, errors: string[]) {
  if (!hasPositiveNumber(configuredTimeoutMs(config))) errors.push(`工具节点 ${nodeKey} 需要配置超时毫秒`)
  if (!hasNonNegativeNumber(config.retryCount)) errors.push(`工具节点 ${nodeKey} 需要配置重试次数`)
  if (!ERROR_BEHAVIORS.has(String(config.errorBehavior || '').trim())) errors.push(`工具节点 ${nodeKey} 需要配置错误行为`)
  if (!hasOutputSchema(config)) errors.push(`工具节点 ${nodeKey} 需要配置输出 Schema`)
}

function validateNodeEndpoints(graph: WorkflowCanvasGraph, errors: string[]) {
  for (const node of graph.nodes) {
    if (node.type === 'END') continue
    const conditions = outgoingConditions(graph, node.nodeKey)
    if (node.type === 'CONDITION') {
      for (const branchKey of conditionBranchKeys(node.config)) {
        if (!conditions.has(branchKey)) errors.push(`条件节点 ${node.nodeKey} 缺少分支 ${branchKey} 下游连接`)
      }
      if (!conditions.has(null)) errors.push(`条件节点 ${node.nodeKey} 缺少默认分支下游连接`)
      continue
    }
    if (node.type === 'INTENT_RECOGNITION') {
      for (const intentKey of intentBranchKeys(node.config)) {
        if (!conditions.has(intentKey)) errors.push(`意图识别节点 ${node.nodeKey} 缺少意图 ${intentKey} 下游连接`)
      }
      if (!conditions.has(null)) errors.push(`意图识别节点 ${node.nodeKey} 缺少兜底分支下游连接`)
      continue
    }
    if (!conditions.has(null)) errors.push(`节点 ${node.nodeKey} 默认出口缺少下游连接`)
  }
}

export function validateWorkflowGraph(graph: WorkflowCanvasGraph): WorkflowValidationResult {
  const errors: string[] = []
  const nodeKeys = new Set(graph.nodes.map((node) => node.nodeKey))

  if (!nodeKeys.has('start')) errors.push('START node is required')
  if (!nodeKeys.has('end')) errors.push('END node is required')

  if (nodeKeys.has('start') && nodeKeys.has('end') && !hasPathToEnd(graph)) {
    errors.push('START must connect to END through at least one path')
  }

  for (const node of graph.nodes) {
    if (node.nodeKey === 'start' || node.nodeKey === 'end') continue
    const connected = graph.edges.some(
      (edge) => edge.sourceNodeKey === node.nodeKey || edge.targetNodeKey === node.nodeKey,
    )
    if (!connected) errors.push(`Node ${node.nodeKey} is not connected`)
    if (node.type === 'LLM' && !node.config.modelConfigId && !node.config.model) {
      errors.push(`大模型节点 ${node.nodeKey} 需要选择模型`)
    }
    if (node.type === 'API_CALL') validateApiGovernance(node.nodeKey, node.config, errors)
    if (node.type === 'TOOL_CALL') validateToolGovernance(node.nodeKey, node.config, errors)
  }
  validateNodeEndpoints(graph, errors)

  return {
    valid: errors.length === 0,
    errors,
  }
}
