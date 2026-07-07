export interface RuntimeOpsDagInput {
  runId: number
  nodes: Record<string, any>[]
}

export interface RuntimeOpsDagNode {
  nodeKey: string
  nodeType: string
  name: string
  status: string
  state: string
  stateLabel: string
  error: string
  selectedUpstreamNodeKeys: string[]
  skippedUpstreamNodeKeys: string[]
}

export interface RuntimeOpsDagEdge {
  source: string
  target: string
  state: 'selected' | 'skipped'
}

export interface RuntimeOpsDagView {
  runId: number
  nodes: RuntimeOpsDagNode[]
  edges: RuntimeOpsDagEdge[]
  summary: Record<'completed' | 'skipped' | 'running' | 'waiting' | 'failed', number>
}

const stateLabels: Record<string, string> = {
  completed: '已完成',
  skipped: '已跳过',
  running: '运行中',
  waiting: '等待中',
  failed: '已失败',
  cancelled: '已取消',
  pending: '待执行',
}

export function buildRuntimeOpsDagView(input: RuntimeOpsDagInput): RuntimeOpsDagView {
  const nodes = (input.nodes || []).map(normalizeRuntimeOpsDagNode)
  const edges = nodes.flatMap((node) => [
    ...node.selectedUpstreamNodeKeys.map((source) => ({ source, target: node.nodeKey, state: 'selected' as const })),
    ...node.skippedUpstreamNodeKeys.map((source) => ({ source, target: node.nodeKey, state: 'skipped' as const })),
  ])
  const summary = {
    completed: 0,
    skipped: 0,
    running: 0,
    waiting: 0,
    failed: 0,
  }
  for (const node of nodes) {
    if (node.state in summary) {
      summary[node.state as keyof typeof summary] += 1
    }
  }
  return { runId: input.runId, nodes, edges, summary }
}

function normalizeRuntimeOpsDagNode(row: Record<string, any>): RuntimeOpsDagNode {
  const selectionState = row.selectionState && typeof row.selectionState === 'object' ? row.selectionState : {}
  const state = normalizeDagState(selectionState.state || row.state || row.status)
  return {
    nodeKey: String(row.nodeKey || row.node_key || ''),
    nodeType: String(row.nodeType || row.node_type || row.type || ''),
    name: String(row.name || row.nodeName || row.nodeKey || row.node_key || ''),
    status: String(row.status || '').toUpperCase(),
    state,
    stateLabel: stateLabels[state] || state,
    error: String(row.error || ''),
    selectedUpstreamNodeKeys: normalizeStringList(selectionState.selectedUpstreamNodeKeys),
    skippedUpstreamNodeKeys: normalizeStringList(selectionState.skippedUpstreamNodeKeys),
  }
}

function normalizeDagState(value: unknown): string {
  const normalized = String(value || '').trim().toLowerCase()
  if (normalized === 'succeeded' || normalized === 'success' || normalized === 'completed' || normalized === 'complete') {
    return 'completed'
  }
  if (normalized === 'skipped' || normalized === 'skip') return 'skipped'
  if (normalized === 'running') return 'running'
  if (normalized === 'waiting' || normalized === 'interrupted') return 'waiting'
  if (normalized === 'failed' || normalized === 'error') return 'failed'
  if (normalized === 'cancelled' || normalized === 'canceled') return 'cancelled'
  return normalized || 'pending'
}

function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.map((item) => String(item || '').trim()).filter(Boolean)
}
