export interface RuntimeOpsNodeDetailInput {
  node: Record<string, any>
  events: Record<string, any>[]
}

export interface RuntimeOpsNodeEventRow {
  key: string
  sequenceLabel: string
  eventType: string
  createdAt: string
  detail: string
}

export interface RuntimeOpsNodeDetailView {
  nodeKey: string
  nodeType: string
  name: string
  status: string
  durationLabel: string
  inputSummary: string
  outputSummary: string
  errorSummary: string
  events: RuntimeOpsNodeEventRow[]
}

const hiddenKeys = new Set([
  '__debug',
  'chainofthought',
  'reasoning',
  'reasoningcontent',
  'reasoning_content',
  'thought',
  'thoughts',
])

export function buildRuntimeOpsNodeDetail(input: RuntimeOpsNodeDetailInput): RuntimeOpsNodeDetailView {
  const node = input.node || {}
  const nodeKey = String(node.nodeKey || node.node_key || '')
  return {
    nodeKey,
    nodeType: String(node.nodeType || node.node_type || ''),
    name: String(node.name || node.nodeName || nodeKey || ''),
    status: String(node.status || '').toUpperCase(),
    durationLabel: durationLabel(node),
    inputSummary: summarizeValue(node.inputs),
    outputSummary: summarizeValue(node.outputs),
    errorSummary: String(node.error || ''),
    events: nodeEvents(input.events || [], nodeKey),
  }
}

function nodeEvents(events: Record<string, any>[], nodeKey: string): RuntimeOpsNodeEventRow[] {
  return events
    .filter((event) => {
      const payload = asRecord(event.payload)
      const eventNodeKey = String(event.nodeId || payload.nodeKey || payload.nodeId || '')
      return eventNodeKey === nodeKey
    })
    .map((event, index) => {
      const payload = asRecord(event.payload)
      return {
        key: String(event.id || `${nodeKey}:${index}`),
        sequenceLabel: `#${String(event.sequence ?? index + 1)}`,
        eventType: String(event.type || 'runtime_event'),
        createdAt: String(event.createdAt || ''),
        detail: summarizeEventDetail(payload, event),
      }
    })
}

function durationLabel(node: Record<string, any>): string {
  const elapsed = Number(node.elapsedMs ?? node.elapsed_ms ?? node.latencyMs ?? 0)
  if (Number.isFinite(elapsed) && elapsed > 0) return `${Math.round(elapsed)}ms`
  return '-'
}

function summarizeValue(value: unknown): string {
  const sanitized = sanitizeValue(value)
  if (sanitized === undefined || sanitized === null || sanitized === '') return '-'
  if (typeof sanitized === 'string') return sanitized
  return JSON.stringify(sanitized)
}

function summarizeEventDetail(payload: Record<string, any>, event: Record<string, any>): string {
  return String(payload.error || payload.reason || payload.message || payload.status || event.error || '').trim()
}

function sanitizeValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sanitizeValue).filter((item) => item !== undefined)
  if (!value || typeof value !== 'object') return value
  const output: Record<string, unknown> = {}
  for (const [key, raw] of Object.entries(value as Record<string, unknown>)) {
    const normalizedKey = key.replace(/[-_\s]/g, '').toLowerCase()
    if (hiddenKeys.has(normalizedKey) || hiddenKeys.has(key.toLowerCase())) continue
    const sanitized = sanitizeValue(raw)
    if (sanitized !== undefined) output[key] = sanitized
  }
  return output
}

function asRecord(value: unknown): Record<string, any> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, any> : {}
}
