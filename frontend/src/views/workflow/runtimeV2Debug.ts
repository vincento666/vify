import { resolveApiUrl } from '@/host/request'
import type { WorkflowRunDebugDetail, WorkflowRunNodeDetail } from './workflowRunDebug'

export type RuntimeV2StartRef = {
  runId?: number
  ownerType?: string
  ownerId?: number
  status?: string
  output?: Record<string, any>
  error?: string
  eventStreamRef?: string
  eventsRef?: string
  nodesRef?: string
  resultRef?: string
}

export type RuntimeV2Event = {
  id?: number | string
  runId?: number
  sequence?: number
  type?: string
  nodeId?: string
  payload?: Record<string, any>
  observability?: Record<string, any>
}

export type RuntimeV2Node = WorkflowRunNodeDetail & {
  runId?: number
  inputs?: Record<string, any>
}

export type RunLogAction = {
  shouldOpenRunDetail: boolean
  runtimeQuery: Record<string, string>
}

export type RuntimeV2EventPage = {
  list?: RuntimeV2Event[]
  total?: number
}

export type RuntimeV2DebugEventObserverOptions = {
  started: RuntimeV2StartRef
  afterSequence?: number
  eventSourceFactory?: (url: string) => EventSource
  listRuntimeV2Events: (runId: number, params: { afterSequence: number }) => Promise<RuntimeV2EventPage>
  onEvents: (events: RuntimeV2Event[]) => void
  onError?: (error: Error) => void
}

export type RuntimeV2DebugEventObserver = {
  close: () => void
  lastSequence: () => number
  markEventsApplied: (events: RuntimeV2Event[]) => RuntimeV2Event[]
}

export function resolveRunLogAction(runId: unknown, runtimeVersion: unknown): RunLogAction {
  const shouldOpenRunDetail = Number(runId || 0) > 0
  const isRuntimeV2 = String(runtimeVersion || '').trim().toLowerCase() === 'v2'
  return {
    shouldOpenRunDetail,
    runtimeQuery: shouldOpenRunDetail && isRuntimeV2 ? { runtime: 'v2' } : {},
  }
}

export function createRuntimeV2DebugDetail(start: RuntimeV2StartRef): WorkflowRunDebugDetail {
  return {
    runId: Number(start.runId || 0),
    ownerType: start.ownerType,
    status: start.status || 'RUNNING',
    output: start.output || {},
    error: start.error || '',
    nodeDetails: [],
  }
}

export function openRuntimeV2DebugEventObserver(
  options: RuntimeV2DebugEventObserverOptions,
): RuntimeV2DebugEventObserver {
  const runId = Number(options.started.runId || 0)
  let lastSequence = Number(options.afterSequence ?? runtimeV2AfterSequenceFromRef(options.started.eventStreamRef) ?? 0)
  let source: EventSource | null = null
  let closed = false
  let recovering: Promise<void> | null = null
  let streamUnavailable = false
  const seen = new Set<string>()

  const recordEvents = (events: RuntimeV2Event[], emit: boolean): RuntimeV2Event[] => {
    const accepted = sortRuntimeV2Events(events).filter((event) => {
      const sequence = Number(event.sequence || 0)
      if (sequence > 0 && sequence <= lastSequence) return false
      const key = runtimeV2EventDedupeKey(event)
      if (seen.has(key)) return false
      seen.add(key)
      if (sequence > 0) lastSequence = Math.max(lastSequence, sequence)
      return true
    })
    if (emit && accepted.length) options.onEvents(accepted)
    return accepted
  }

  const openStream = () => {
    if (closed || !runId || streamUnavailable) return
    try {
      source = (options.eventSourceFactory || createRuntimeV2EventSource)(
        runtimeV2EventStreamUrl(options.started, lastSequence),
      )
      source.onmessage = (message) => {
        const event = parseRuntimeV2StreamMessage(message)
        if (event) recordEvents([event], true)
      }
      source.onerror = () => {
        if (closed) return
        source?.close()
        source = null
        void recoverDurableEvents()
      }
      source.addEventListener?.('runtime_v2_event', ((message: MessageEvent) => {
        const event = parseRuntimeV2StreamMessage(message)
        if (event) recordEvents([event], true)
      }) as EventListener)
    } catch (error) {
      streamUnavailable = true
      options.onError?.(toRuntimeV2StreamError(error))
    }
  }

  const recoverDurableEvents = async () => {
    if (closed || recovering || !runId) return recovering
    recovering = (async () => {
      try {
        const page = await options.listRuntimeV2Events(runId, { afterSequence: lastSequence })
        recordEvents(page.list || [], true)
      } catch (error) {
        options.onError?.(toRuntimeV2StreamError(error))
      } finally {
        recovering = null
        if (!closed) openStream()
      }
    })()
    return recovering
  }

  openStream()

  return {
    close: () => {
      closed = true
      source?.close()
      source = null
    },
    lastSequence: () => lastSequence,
    markEventsApplied: (events) => recordEvents(events, false),
  }
}

export function applyRuntimeV2EventsToDebugDetail(
  detail: WorkflowRunDebugDetail,
  events: RuntimeV2Event[],
): WorkflowRunDebugDetail {
  return events.reduce((current, event) => applyRuntimeV2EventToDebugDetail(current, event), detail)
}

export function applyRuntimeV2NodesToDebugDetail(
  detail: WorkflowRunDebugDetail,
  nodes: RuntimeV2Node[],
): WorkflowRunDebugDetail {
  if (!nodes.length) return detail
  const merged = new Map<string, WorkflowRunNodeDetail>()
  for (const node of detail.nodeDetails || []) {
    const key = runtimeNodeKey(node)
    if (key) merged.set(key, node)
  }
  for (const node of nodes) {
    const key = runtimeNodeKey(node)
    if (!key) continue
    const current = merged.get(key) || {}
    merged.set(key, {
      ...current,
      id: node.id ?? current.id,
      nodeKey: node.nodeKey || current.nodeKey,
      nodeType: node.nodeType || current.nodeType,
      status: normalizeRuntimeNodeStatus(node.status || current.status),
      selectionState: node.selectionState || current.selectionState,
      elapsedMs: Number(node.elapsedMs ?? current.elapsedMs ?? 0),
      latencyMs: Number(node.latencyMs ?? current.latencyMs ?? 0),
      outputs: node.outputs || current.outputs || {},
      error: node.error || current.error || '',
      errorSummary: node.errorSummary || node.error || current.errorSummary || current.error || '',
      events: current.events || [],
    })
  }
  return { ...detail, nodeDetails: Array.from(merged.values()) }
}

export function mergeRuntimeV2RunToDebugDetail(
  detail: WorkflowRunDebugDetail,
  run: RuntimeV2StartRef,
): WorkflowRunDebugDetail {
  return {
    ...detail,
    runId: Number(run.runId || detail.runId || 0),
    ownerType: run.ownerType || detail.ownerType,
    status: normalizeRuntimeRunStatus(run.status || detail.status),
    output: run.output || detail.output || {},
    error: run.error || detail.error || '',
  }
}

export function isRuntimeV2TerminalStatus(status: unknown): boolean {
  return ['COMPLETED', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'CANCELED', 'TIMEOUT', 'TIMED_OUT', 'INTERRUPTED', 'WAITING']
    .includes(String(status || '').trim().toUpperCase())
}

function applyRuntimeV2EventToDebugDetail(
  detail: WorkflowRunDebugDetail,
  event: RuntimeV2Event,
): WorkflowRunDebugDetail {
  const status = runtimeEventNodeStatus(event)
  const nodeKey = String(event.nodeId || event.payload?.nodeKey || '').trim()
  const nodeType = String(event.payload?.nodeType || '').trim()
  const error = String(event.payload?.error || '').trim()
  let next: WorkflowRunDebugDetail = {
    ...detail,
    status: runtimeEventRunStatus(event, detail.status),
    error: error || detail.error || '',
  }

  if (nodeKey && status) {
    next = upsertRuntimeNode(next, {
      id: event.payload?.nodeRunId,
      nodeKey,
      nodeType,
      status,
      error,
      errorSummary: error,
      outputs: runtimeEventOutputs(event),
      selectionState: runtimeEventSelectionState(event),
      events: [event],
    })
  }

  if (status === 'FAILED') {
    next = {
      ...next,
      status: 'FAILED',
      error: error || next.error || '运行失败',
    }
  }
  return next
}

function upsertRuntimeNode(
  detail: WorkflowRunDebugDetail,
  patch: WorkflowRunNodeDetail,
): WorkflowRunDebugDetail {
  const nodes = [...(detail.nodeDetails || [])]
  const key = runtimeNodeKey(patch)
  const index = nodes.findIndex((node) => runtimeNodeKey(node) === key)
  const current = index >= 0 ? nodes[index] : {}
  const nextNode: WorkflowRunNodeDetail = {
    ...current,
    ...patch,
    id: patch.id ?? current.id,
    nodeKey: patch.nodeKey || current.nodeKey,
    nodeType: patch.nodeType || current.nodeType,
    status: normalizeRuntimeNodeStatus(patch.status || current.status),
    selectionState: patch.selectionState || current.selectionState,
    elapsedMs: Number(patch.elapsedMs ?? current.elapsedMs ?? 0),
    outputs: patch.outputs ?? current.outputs ?? {},
    events: [...(current.events || []), ...(patch.events || [])],
  }
  if (index >= 0) nodes[index] = nextNode
  else nodes.push(nextNode)
  return { ...detail, nodeDetails: nodes }
}

function runtimeEventNodeStatus(event: RuntimeV2Event): string {
  const observed = String(event.observability?.nodeState || '').trim()
  if (observed) return normalizeRuntimeNodeStatus(observed)
  const payloadStatus = String(event.payload?.status || '').trim()
  if (payloadStatus) return normalizeRuntimeNodeStatus(payloadStatus)
  return normalizeRuntimeNodeStatus({
    workflow_node_started: 'RUNNING',
    workflow_node_completed: 'COMPLETED',
    workflow_node_failed: 'FAILED',
    workflow_node_waiting: 'WAITING',
    workflow_node_skipped: 'SKIPPED',
  }[String(event.type || '')] || '')
}

function runtimeEventOutputs(event: RuntimeV2Event): Record<string, any> | undefined {
  const payload = event.payload || {}
  const outputs = payload.outputs ?? payload.output
  return isRuntimeRecord(outputs) ? outputs : undefined
}

function runtimeEventSelectionState(event: RuntimeV2Event): WorkflowRunNodeDetail['selectionState'] | undefined {
  const selectionState = event.payload?.selectionState
  return isRuntimeRecord(selectionState) ? (selectionState as WorkflowRunNodeDetail['selectionState']) : undefined
}

function isRuntimeRecord(value: unknown): value is Record<string, any> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function runtimeEventRunStatus(event: RuntimeV2Event, fallback: string | undefined): string {
  const eventType = String(event.type || '')
  const payloadStatus = String(event.payload?.status || '').trim()
  if (payloadStatus && !String(event.nodeId || '').trim()) return normalizeRuntimeRunStatus(payloadStatus)
  if (eventType === 'workflow_run_completed') return 'SUCCEEDED'
  if (eventType === 'workflow_run_cancelled') return 'CANCELLED'
  if (eventType === 'workflow_run_failed' || runtimeEventNodeStatus(event) === 'FAILED') return 'FAILED'
  return normalizeRuntimeRunStatus(fallback || 'RUNNING')
}

function runtimeNodeKey(node: WorkflowRunNodeDetail): string {
  return String(node.nodeKey || node.id || '').trim()
}

function normalizeRuntimeRunStatus(status: unknown): string {
  const normalized = String(status || '').trim().toUpperCase()
  if (normalized === 'COMPLETED') return 'SUCCEEDED'
  return normalized || 'RUNNING'
}

function normalizeRuntimeNodeStatus(status: unknown): string {
  const normalized = String(status || '').trim().toUpperCase()
  if (normalized === 'SUCCEEDED') return 'COMPLETED'
  return normalized
}

function createRuntimeV2EventSource(url: string): EventSource {
  if (typeof EventSource === 'undefined') throw new Error('EventSource is unavailable')
  return new EventSource(url)
}

function runtimeV2EventStreamUrl(started: RuntimeV2StartRef, afterSequence: number): string {
  const runId = Number(started.runId || 0)
  const path = started.eventStreamRef || `/api/v1/runtime-runs/${runId}/events/stream`
  return resolveApiUrl(withRuntimeV2AfterSequence(path, afterSequence))
}

function withRuntimeV2AfterSequence(path: string, afterSequence: number): string {
  const base = 'http://hify.local'
  const url = new URL(path || '/', base)
  url.searchParams.set('afterSequence', String(Math.max(0, Number(afterSequence || 0))))
  if (/^https?:\/\//i.test(path)) return url.toString()
  return `${url.pathname}${url.search}${url.hash}`
}

function runtimeV2AfterSequenceFromRef(ref: string | undefined): number | undefined {
  if (!ref) return undefined
  try {
    const value = new URL(ref, 'http://hify.local').searchParams.get('afterSequence')
    if (value === null) return undefined
    const sequence = Number(value)
    return Number.isFinite(sequence) ? sequence : undefined
  } catch {
    return undefined
  }
}

function parseRuntimeV2StreamMessage(message: MessageEvent | { data?: unknown }): RuntimeV2Event | null {
  const data = String(message.data || '').trim()
  if (!data || data === '[DONE]') return null
  return JSON.parse(data) as RuntimeV2Event
}

function sortRuntimeV2Events(events: RuntimeV2Event[]): RuntimeV2Event[] {
  return events
    .map((event, index) => ({ event, index, sequence: Number(event.sequence || 0) }))
    .sort((left, right) => {
      const leftSequence = left.sequence > 0 ? left.sequence : Number.MAX_SAFE_INTEGER
      const rightSequence = right.sequence > 0 ? right.sequence : Number.MAX_SAFE_INTEGER
      return leftSequence - rightSequence || left.index - right.index
    })
    .map(({ event }) => event)
}

function runtimeV2EventDedupeKey(event: RuntimeV2Event): string {
  const sequence = Number(event.sequence || 0)
  if (sequence > 0) return `sequence:${sequence}`
  return [
    'event',
    String(event.id || ''),
    String(event.type || ''),
    String(event.nodeId || event.payload?.nodeKey || ''),
  ].join(':')
}

function toRuntimeV2StreamError(error: unknown): Error {
  if (error instanceof Error) return new Error(`Runtime v2 event stream failed: ${error.message}`)
  return new Error('Runtime v2 event stream failed')
}
