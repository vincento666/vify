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
  const endNodeKeys = new Set(graph.nodes.filter((node) => node.type === 'END').map((node) => node.nodeKey))
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
    if (endNodeKeys.has(current)) return true
    if (seen.has(current)) continue
    seen.add(current)
    stack.push(...(adjacency.get(current) || []))
  }
  return false
}

function reachableNodeKeys(graph: WorkflowCanvasGraph) {
  const adjacency = new Map<string, string[]>()
  for (const edge of graph.edges) {
    const next = adjacency.get(edge.sourceNodeKey) || []
    next.push(edge.targetNodeKey)
    adjacency.set(edge.sourceNodeKey, next)
  }

  const startKeys = graph.nodes
    .filter((node) => node.type === 'START' || node.nodeKey === 'start')
    .map((node) => node.nodeKey)
  const seen = new Set<string>()
  const stack = [...startKeys]
  while (stack.length > 0) {
    const current = stack.pop()!
    if (seen.has(current)) continue
    seen.add(current)
    stack.push(...(adjacency.get(current) || []).filter((nodeKey) => !seen.has(nodeKey)))
  }
  return seen
}

function normalizeBranchKey(value: unknown) {
  const text = String(value ?? '').trim()
  return text.length > 0 ? text : null
}

function edgeSourcePortKey(edge: { condition?: string | null; sourcePortKey?: string | null }) {
  return normalizeBranchKey(edge.sourcePortKey) || normalizeBranchKey(edge.condition) || 'default'
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

function isTruthy(value: unknown) {
  if (typeof value === 'boolean') return value
  return ['1', 'true', 'yes', 'on'].includes(String(value ?? '').trim().toLowerCase())
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
    if (conditions.size === 0 && isSideEffectTerminalNode(graph, node.nodeKey)) continue
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

function isSideEffectTerminalNode(graph: WorkflowCanvasGraph, nodeKey: string) {
  const node = graph.nodes.find((item) => item.nodeKey === nodeKey)
  if (node && isTruthy(node.config.sideEffectTerminal)) return true
  return graph.edges.some((edge) => edge.targetNodeKey === nodeKey && isTruthy(edge.sideEffectTerminal))
}

function hasReachableSideEffectTerminal(graph: WorkflowCanvasGraph) {
  const reachable = reachableNodeKeys(graph)
  const outgoingCounts = new Map<string, number>()
  for (const edge of graph.edges) {
    outgoingCounts.set(edge.sourceNodeKey, (outgoingCounts.get(edge.sourceNodeKey) || 0) + 1)
  }
  return graph.nodes.some(
    (node) =>
      node.type !== 'START' &&
      node.type !== 'END' &&
      reachable.has(node.nodeKey) &&
      !outgoingCounts.has(node.nodeKey) &&
      isSideEffectTerminalNode(graph, node.nodeKey),
  )
}

function allowsFanOut(graph: WorkflowCanvasGraph, nodeKey: string, portKey: string) {
  const node = graph.nodes.find((item) => item.nodeKey === nodeKey)
  if (!node) return true
  if (node.type === 'CONDITION' || node.type === 'INTENT_RECOGNITION') return true
  if (portKey !== 'default') return true
  if (isTruthy(node.config.allowFanOut)) return true
  for (const fieldName of ['ports', 'outputPorts']) {
    const ports = node.config[fieldName]
    if (!Array.isArray(ports)) continue
    if (ports.some((port) => (normalizeBranchKey(port?.key ?? port?.name) || 'default') === portKey && isTruthy(port?.allowFanOut))) {
      return true
    }
  }
  return false
}

function validateFanOut(graph: WorkflowCanvasGraph, errors: string[]) {
  const targetsBySourcePort = new Map<string, Set<string>>()
  for (const edge of graph.edges) {
    const portKey = edgeSourcePortKey(edge)
    const mapKey = `${edge.sourceNodeKey}::${portKey}`
    const targets = targetsBySourcePort.get(mapKey) || new Set<string>()
    targets.add(edge.targetNodeKey)
    targetsBySourcePort.set(mapKey, targets)
  }
  for (const [mapKey, targets] of targetsBySourcePort) {
    if (targets.size <= 1) continue
    const [nodeKey, portKey] = mapKey.split('::')
    if (allowsFanOut(graph, nodeKey, portKey)) continue
    errors.push(`节点 ${nodeKey} ${portKey} 出口需要开启 fan-out 后才能连接多个下游`)
  }
}

export function validateWorkflowGraph(graph: WorkflowCanvasGraph): WorkflowValidationResult {
  const errors: string[] = []
  const nodeKeys = new Set(graph.nodes.map((node) => node.nodeKey))
  const hasEndNode = graph.nodes.some((node) => node.type === 'END')
  const reachable = reachableNodeKeys(graph)

  if (!nodeKeys.has('start')) errors.push('START node is required')
  if (!hasEndNode) errors.push('END node is required')

  if (nodeKeys.has('start') && hasEndNode && !hasPathToEnd(graph) && !hasReachableSideEffectTerminal(graph)) {
    errors.push('START must connect to END through at least one path')
  }

  for (const node of graph.nodes) {
    if (node.type === 'START' || node.type === 'END') continue
    const connected = graph.edges.some(
      (edge) => edge.sourceNodeKey === node.nodeKey || edge.targetNodeKey === node.nodeKey,
    )
    if (!connected) errors.push(`Node ${node.nodeKey} is not connected`)
    else if (!reachable.has(node.nodeKey)) errors.push(`Node ${node.nodeKey} is not reachable from START`)
    if (node.type === 'LLM' && !node.config.modelConfigId && !node.config.model) {
      errors.push(`大模型节点 ${node.nodeKey} 需要选择模型`)
    }
    if (
      node.type === 'INTENT_RECOGNITION'
      && String(node.config.classifierMode || node.config.classifier_mode || '').toLowerCase() === 'llm'
      && !node.config.modelConfigId
      && !node.config.model_config_id
    ) {
      errors.push(`意图识别节点 ${node.nodeKey} 需要选择模型`)
    }
    if (node.type === 'API_CALL') validateApiGovernance(node.nodeKey, node.config, errors)
    if (node.type === 'TOOL_CALL') validateToolGovernance(node.nodeKey, node.config, errors)
  }
  validateNodeEndpoints(graph, errors)
  validateFanOut(graph, errors)

  return {
    valid: errors.length === 0,
    errors,
  }
}
