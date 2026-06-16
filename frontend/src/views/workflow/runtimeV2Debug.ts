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
      outputs: event.payload?.output || {},
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
    elapsedMs: Number(patch.elapsedMs ?? current.elapsedMs ?? 0),
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
