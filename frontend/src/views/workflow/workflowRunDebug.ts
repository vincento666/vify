export type WorkflowRunNodeDetail = {
  id?: number | string
  nodeKey?: string
  nodeType?: string
  status?: string
  elapsedMs?: number
  latencyMs?: number
  outputs?: Record<string, any>
  error?: string
  inputSummary?: string
  outputSummary?: string
  errorSummary?: string
  inputTokens?: number
  outputTokens?: number
  totalTokens?: number
  costEstimate?: string | number | null
  usageEstimated?: boolean
  resourceType?: string
  resourceId?: string | number
  events?: any[]
}

export type WorkflowRunDebugDetail = {
  runId?: number
  ownerType?: string
  status?: string
  elapsedMs?: number
  input?: Record<string, any>
  output?: Record<string, any>
  error?: string
  nodeDetails?: WorkflowRunNodeDetail[]
}

export type WorkflowRunSummary = {
  runLabel: string
  statusLabel: string
  elapsedLabel: string
  nodeCountLabel: string
}

export type WorkflowRunCallTreeRow = {
  detailKey: string
  nodeKey: string
  nodeType: string
  status: string
  elapsedMs: number
}

export type WorkflowRunFlamegraphRow = {
  detailKey: string
  nodeKey: string
  label: string
  startMs: number
  durationMs: number
  status: string
}

export type WorkflowNodeEventEvidenceRow = {
  key: string
  sequenceLabel: string
  eventType: string
  status: string
  detail: string
}

export function summarizeWorkflowRunDebug(detail: WorkflowRunDebugDetail | null | undefined): WorkflowRunSummary {
  const nodeCount = normalizeNodes(detail).length
  return {
    runLabel: detail?.runId ? `Run #${detail.runId}` : '尚未运行',
    statusLabel: String(detail?.status || '等待试运行'),
    elapsedLabel: `${Number(detail?.elapsedMs || 0)}ms`,
    nodeCountLabel: `${nodeCount} ${nodeCount === 1 ? 'node' : 'nodes'}`,
  }
}

export function buildWorkflowRunCallTree(detail: WorkflowRunDebugDetail | null | undefined): WorkflowRunCallTreeRow[] {
  return visibleTraceNodes(detail).map(({ node, index }) => ({
    detailKey: workflowRunNodeDetailKey(node, index),
    nodeKey: String(node.nodeKey || ''),
    nodeType: String(node.nodeType || ''),
    status: String(node.status || ''),
    elapsedMs: Number(node.elapsedMs || 0),
  }))
}

export function buildWorkflowRunFlamegraph(detail: WorkflowRunDebugDetail | null | undefined): WorkflowRunFlamegraphRow[] {
  let cursor = 0
  return visibleTraceNodes(detail).map(({ node, index }) => {
    const duration = Number(node.elapsedMs || 0)
    const row = {
      detailKey: workflowRunNodeDetailKey(node, index),
      nodeKey: String(node.nodeKey || ''),
      label: `${String(node.nodeType || '')} ${String(node.nodeKey || '')}`.trim(),
      startMs: cursor,
      durationMs: duration,
      status: String(node.status || ''),
    }
    cursor += duration
    return row
  })
}

export function formatWorkflowDebugValue(value: any): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}

export function formatWorkflowNodeEvidence(node: WorkflowRunNodeDetail | null | undefined): string {
  const totalTokens = Number(node?.totalTokens ?? 0)
  const inputTokens = Number(node?.inputTokens ?? 0)
  const outputTokens = Number(node?.outputTokens ?? 0)
  const tokenLabel = node?.usageEstimated
    ? `Tokens ${totalTokens} (estimated)`
    : `Tokens ${totalTokens} (${inputTokens} in / ${outputTokens} out)`
  const cost = node?.costEstimate === null || node?.costEstimate === undefined || node?.costEstimate === ''
    ? '-'
    : String(node.costEstimate)
  const latency = Number(node?.latencyMs ?? node?.elapsedMs ?? 0)
  const resource = [node?.resourceType || node?.nodeType || '', node?.resourceId || '']
    .filter(Boolean)
    .join(' ')
  return `${tokenLabel} · Cost ${cost} · ${latency}ms${resource ? ` · ${resource}` : ''}`
}

export function formatWorkflowLlmFallbackEvidence(node: WorkflowRunNodeDetail | null | undefined): string {
  const llm = debugLlmPayload(node)
  const fallback = llm?.fallback
  if (!llm || (!llm.fallbackUsed && !fallback?.attempted)) return ''

  const parts = [llm.fallbackUsed ? 'Fallback used' : 'Fallback attempted']
  const models = [
    llm.requestModel ? `request ${redactDebugText(llm.requestModel)}` : '',
    llm.fallbackModel ? `fallback ${redactDebugText(llm.fallbackModel)}` : '',
  ].filter(Boolean)
  if (models.length) parts.push(models.join(' -> '))
  if (llm.fallbackReason) parts.push(`reason ${redactDebugText(llm.fallbackReason)}`)

  const attempts = Array.isArray(fallback?.attempts) ? fallback.attempts : []
  if (attempts.length) {
    parts.push(attempts.map(formatFallbackAttempt).join('; '))
  }
  return parts.join(' · ')
}

export function formatWorkflowNodeEventEvidence(
  node: WorkflowRunNodeDetail | null | undefined,
): WorkflowNodeEventEvidenceRow[] {
  const events = Array.isArray(node?.events) ? node.events : []
  return events.map((event, index) => {
    const eventRecord = asDebugRecord(event)
    const payload = asDebugRecord(eventRecord.payload)
    const observability = asDebugRecord(eventRecord.observability)
    const eventId = eventRecord.id ?? `${node?.nodeKey || 'node'}:${index}`
    return {
      key: `event:${String(eventId)}`,
      sequenceLabel: `#${String(eventRecord.sequence ?? index + 1)}`,
      eventType: String(eventRecord.type || 'runtime_event'),
      status: runtimeEventStatus(payload, observability, node?.status),
      detail: redactDebugText(runtimeEventDetail(payload, eventRecord)),
    }
  })
}

export function workflowRunNodeDetailKey(node: WorkflowRunNodeDetail, index: number): string {
  const id = node.id ?? ''
  if (id !== '') return `id:${String(id)}`
  return `idx:${index}:${String(node.nodeKey || '')}`
}

function normalizeNodes(detail: WorkflowRunDebugDetail | null | undefined): WorkflowRunNodeDetail[] {
  return Array.isArray(detail?.nodeDetails) ? detail.nodeDetails : []
}

function visibleTraceNodes(detail: WorkflowRunDebugDetail | null | undefined): Array<{ node: WorkflowRunNodeDetail; index: number }> {
  return normalizeNodes(detail)
    .map((node, index) => ({ node, index }))
    .filter(({ node }) => !['START', 'END'].includes(String(node.nodeType || '').toUpperCase()))
}

function debugLlmPayload(node: WorkflowRunNodeDetail | null | undefined): Record<string, any> | null {
  const outputs = node?.outputs || {}
  const debug = outputs.__debug
  const llm = debug?.llm
  return llm && typeof llm === 'object' ? llm : null
}

function asDebugRecord(value: any): Record<string, any> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
}

function runtimeEventStatus(
  payload: Record<string, any>,
  observability: Record<string, any>,
  fallback: any,
): string {
  return String(observability.nodeState || payload.status || fallback || '').trim().toUpperCase()
}

function runtimeEventDetail(payload: Record<string, any>, event: Record<string, any>): string {
  return String(payload.reason || payload.error || payload.message || payload.detail || event.error || '').trim()
}

function formatFallbackAttempt(attempt: Record<string, any>): string {
  const model = redactDebugText(attempt.model || 'unknown model')
  const status = redactDebugText(attempt.status || 'unknown')
  const reason = attempt.reason ? ` (${redactDebugText(attempt.reason)})` : ''
  return `${model} ${status}${reason}`
}

function redactDebugText(value: any): string {
  return String(value)
    .replace(/\b(api[-_]?key|token|authorization|password|secret|credential)s?\s*[:=]\s*[^,\s;)]+/gi, '$1=[REDACTED]')
    .replace(/\bsk-[A-Za-z0-9_-]+/g, '[REDACTED]')
    .replace(/\bBearer\s+[A-Za-z0-9._-]+/gi, 'Bearer [REDACTED]')
}
