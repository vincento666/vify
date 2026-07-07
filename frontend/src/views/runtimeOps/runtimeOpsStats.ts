export interface RuntimeOpsStatsInput {
  nodes: Record<string, any>[]
  events: Record<string, any>[]
  jobs: Record<string, any>[]
  dlq: Record<string, any>[]
}

export interface RuntimeOpsCallStat {
  kind: RuntimeOpsCallKind
  label: string
  total: number
  failed: number
  retries: number
}

export interface RuntimeOpsFailureItem {
  key: string
  source: 'event' | 'job' | 'dlq'
  sourceLabel: string
  kind: RuntimeOpsCallKind | 'runtime'
  kindLabel: string
  target: string
  status: string
  retryLabel: string
  message: string
}

export interface RuntimeOpsStatsView {
  callStats: RuntimeOpsCallStat[]
  failureItems: RuntimeOpsFailureItem[]
}

type RuntimeOpsCallKind = 'provider' | 'api' | 'tool'

const callKinds: Array<{ kind: RuntimeOpsCallKind; label: string }> = [
  { kind: 'provider', label: 'Provider' },
  { kind: 'api', label: 'API' },
  { kind: 'tool', label: 'Tool' },
]

const failedStatuses = new Set(['FAILED', 'CANCELLED'])

export function buildRuntimeOpsStatsView(input: RuntimeOpsStatsInput): RuntimeOpsStatsView {
  const counters = new Map<RuntimeOpsCallKind, RuntimeOpsCallStat>(
    callKinds.map((item) => [item.kind, { ...item, total: 0, failed: 0, retries: 0 }]),
  )
  const countedNodeKeys = new Set<string>()
  const failedNodeKeys = new Set<string>()

  for (const node of input.nodes || []) {
    const kind = callKindFromNode(node)
    if (!kind) continue
    const nodeKey = nodeKeyOf(node)
    const counter = counters.get(kind)
    if (!counter) continue
    counter.total += 1
    if (nodeKey) countedNodeKeys.add(nodeKey)
    if (failedStatuses.has(String(node.status || '').toUpperCase())) {
      counter.failed += 1
      if (nodeKey) failedNodeKeys.add(nodeKey)
    }
  }

  const failureItems: RuntimeOpsFailureItem[] = []
  for (const [index, event] of (input.events || []).entries()) {
    const payload = asRecord(event.payload)
    const kind = callKindFromEvent(event)
    if (kind && String(event.type || '') === 'workflow_node_external_call_failed') {
      const counter = counters.get(kind)
      const eventNodeKey = String(event.nodeId || payload.nodeKey || payload.nodeId || '')
      if (counter) {
        if (eventNodeKey && !countedNodeKeys.has(eventNodeKey)) {
          counter.total += 1
          countedNodeKeys.add(eventNodeKey)
        }
        if (!eventNodeKey || !failedNodeKeys.has(eventNodeKey)) {
          counter.failed += 1
          if (eventNodeKey) failedNodeKeys.add(eventNodeKey)
        }
        counter.retries += nonNegativeInt(payload.retryCount ?? payload.retry_count, 0)
      }
      failureItems.push(eventFailureItem(event, payload, kind, index))
    }
  }

  for (const job of input.jobs || []) {
    if (!shouldShowJobFailure(job)) continue
    failureItems.push(jobFailureItem(job, 'job'))
  }
  for (const job of input.dlq || []) {
    failureItems.push(jobFailureItem(job, 'dlq'))
  }

  return {
    callStats: callKinds.map((item) => counters.get(item.kind) || { ...item, total: 0, failed: 0, retries: 0 }),
    failureItems,
  }
}

function eventFailureItem(
  event: Record<string, any>,
  payload: Record<string, any>,
  kind: RuntimeOpsCallKind,
  index: number,
): RuntimeOpsFailureItem {
  const errorKind = String(payload.errorKind || payload.error_kind || '').trim()
  const message = String(payload.message || payload.error || event.error || '').trim()
  const attempts = nonNegativeInt(payload.attempts, 0)
  const retryCount = nonNegativeInt(payload.retryCount ?? payload.retry_count, 0)
  const retryParts = []
  if (attempts > 0) retryParts.push(`attempts ${attempts}`)
  retryParts.push(`retries ${retryCount}`)
  if (payload.breakerOpen || payload.breaker_open) retryParts.push('breaker open')
  return {
    key: `event:${String(event.id || index)}`,
    source: 'event',
    sourceLabel: 'Event',
    kind,
    kindLabel: labelForKind(kind),
    target: String(payload.providerKey || payload.provider_key || event.nodeId || payload.nodeKey || 'external call'),
    status: errorKind || 'failed',
    retryLabel: retryParts.join(', '),
    message: [errorKind, message].filter(Boolean).join(': '),
  }
}

function jobFailureItem(job: Record<string, any>, source: 'job' | 'dlq'): RuntimeOpsFailureItem {
  const target = `${source === 'job' ? 'Job' : 'DLQ'} #${Number(job.jobId || 0)}`
  const attemptCount = nonNegativeInt(job.attemptCount, 0)
  const maxAttempts = nonNegativeInt(job.maxAttempts, 0)
  const retryParts = [maxAttempts > 0 ? `${attemptCount} / ${maxAttempts}` : String(attemptCount)]
  const nextRetryAt = String(job.nextRetryAt || job.availableAt || '')
  if (nextRetryAt) retryParts.push(`next ${nextRetryAt}`)
  return {
    key: `${source}:${Number(job.jobId || 0)}`,
    source,
    sourceLabel: source === 'job' ? 'Job Queue' : 'DLQ',
    kind: 'runtime',
    kindLabel: 'Runtime',
    target,
    status: String(job.status || '').toUpperCase(),
    retryLabel: retryParts.join(', '),
    message: String(job.lastError || ''),
  }
}

function shouldShowJobFailure(job: Record<string, any>): boolean {
  const status = String(job.status || '').toUpperCase()
  return status === 'FAILED' || Boolean(job.lastError) || Boolean(job.nextRetryAt || job.availableAt)
}

function callKindFromNode(node: Record<string, any>): RuntimeOpsCallKind | null {
  return callKindFromParts(String(node.nodeType || node.node_type || ''), '')
}

function callKindFromEvent(event: Record<string, any>): RuntimeOpsCallKind | null {
  const payload = asRecord(event.payload)
  return callKindFromParts(String(payload.callType || payload.call_type || payload.nodeType || ''), String(payload.providerKey || ''))
}

function callKindFromParts(callType: string, providerKey: string): RuntimeOpsCallKind | null {
  const normalizedType = callType.toUpperCase()
  const normalizedProviderKey = providerKey.toLowerCase()
  if (normalizedType === 'LLM' || normalizedType === 'PROVIDER' || normalizedProviderKey.startsWith('llm:')) return 'provider'
  if (normalizedType === 'API' || normalizedType === 'API_CALL' || normalizedProviderKey.startsWith('api:')) return 'api'
  if (normalizedType === 'TOOL' || normalizedType === 'TOOL_CALL' || normalizedProviderKey.startsWith('tool:')) return 'tool'
  return null
}

function labelForKind(kind: RuntimeOpsCallKind) {
  return callKinds.find((item) => item.kind === kind)?.label || kind
}

function nodeKeyOf(node: Record<string, any>): string {
  return String(node.nodeKey || node.node_key || '')
}

function nonNegativeInt(value: unknown, fallback: number): number {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) return fallback
  return Math.trunc(parsed)
}

function asRecord(value: unknown): Record<string, any> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, any> : {}
}
