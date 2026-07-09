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
  joinState: string
  joinStateLabel: string
  joinWaitingOnNodeKeys: string[]
  parallelWaveKey: string
  startedAt: string
  finishedAt: string
}

export interface RuntimeOpsDagEdge {
  source: string
  target: string
  state: 'selected' | 'skipped'
  stateLabel: string
}

export interface RuntimeOpsParallelWave {
  key: string
  nodeKeys: string[]
  overlap: boolean
  overlapLabel: string
}

export interface RuntimeOpsDagView {
  runId: number
  nodes: RuntimeOpsDagNode[]
  edges: RuntimeOpsDagEdge[]
  parallelWaves: RuntimeOpsParallelWave[]
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

const edgeStateLabels = {
  selected: '已选择',
  skipped: '已跳过',
}

const joinStateLabels: Record<string, string> = {
  waiting: '等待汇合',
  ready: '可汇合',
  completed: '已汇合',
}

export function buildRuntimeOpsDagView(input: RuntimeOpsDagInput): RuntimeOpsDagView {
  const nodes = (input.nodes || []).map(normalizeRuntimeOpsDagNode)
  const edges = nodes.flatMap((node) => [
    ...node.selectedUpstreamNodeKeys.map((source) => ({
      source,
      target: node.nodeKey,
      state: 'selected' as const,
      stateLabel: edgeStateLabels.selected,
    })),
    ...node.skippedUpstreamNodeKeys.map((source) => ({
      source,
      target: node.nodeKey,
      state: 'skipped' as const,
      stateLabel: edgeStateLabels.skipped,
    })),
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
  return { runId: input.runId, nodes, edges, parallelWaves: buildParallelWaves(nodes), summary }
}

function normalizeRuntimeOpsDagNode(row: Record<string, any>): RuntimeOpsDagNode {
  const selectionState = row.selectionState && typeof row.selectionState === 'object' ? row.selectionState : {}
  const state = normalizeDagState(selectionState.state || row.state || row.status)
  const join = normalizeJoinState(selectionState, state)
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
    joinState: join.state,
    joinStateLabel: join.label,
    joinWaitingOnNodeKeys: join.waitingOnNodeKeys,
    parallelWaveKey: String(selectionState.parallelWaveKey || selectionState.waveKey || ''),
    startedAt: String(row.startedAt || row.started_at || row.createdAt || row.created_at || row.startTime || ''),
    finishedAt: String(row.finishedAt || row.finished_at || row.completedAt || row.endTime || ''),
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

function normalizeJoinState(selectionState: Record<string, any>, nodeState: string) {
  const join = selectionState.join && typeof selectionState.join === 'object' ? selectionState.join : null
  if (!join) return { state: '', label: '', waitingOnNodeKeys: [] as string[] }
  const required = normalizeStringList(join.requiredUpstreamNodeKeys)
  const completed = new Set(normalizeStringList(join.completedUpstreamNodeKeys))
  const skipped = new Set(normalizeStringList(join.skippedUpstreamNodeKeys))
  const waitingOnNodeKeys = required.filter((nodeKey) => !completed.has(nodeKey) && !skipped.has(nodeKey))
  const explicitState = normalizeDagState(join.state)
  const state = explicitState !== 'pending'
    ? explicitState
    : nodeState === 'completed'
      ? 'completed'
      : waitingOnNodeKeys.length
        ? 'waiting'
        : 'ready'
  return {
    state,
    label: joinStateLabels[state] || state,
    waitingOnNodeKeys,
  }
}

function buildParallelWaves(nodes: RuntimeOpsDagNode[]): RuntimeOpsParallelWave[] {
  const groups = new Map<string, RuntimeOpsDagNode[]>()
  for (const node of nodes) {
    if (!node.parallelWaveKey) continue
    groups.set(node.parallelWaveKey, [...(groups.get(node.parallelWaveKey) || []), node])
  }
  return Array.from(groups.entries())
    .filter(([, group]) => group.length > 1)
    .map(([key, group]) => ({
      key,
      nodeKeys: group.map((node) => node.nodeKey),
      overlap: hasTimelineOverlap(group),
      overlapLabel: hasTimelineOverlap(group) ? '并行重叠' : '未重叠',
    }))
}

function hasTimelineOverlap(nodes: RuntimeOpsDagNode[]): boolean {
  const intervals = nodes
    .map((node) => [Date.parse(node.startedAt), Date.parse(node.finishedAt)] as const)
    .filter(([start, end]) => Number.isFinite(start) && Number.isFinite(end) && end >= start)
    .sort(([leftStart], [rightStart]) => leftStart - rightStart)
  let latestEnd = -Infinity
  for (const [start, end] of intervals) {
    if (start < latestEnd) return true
    latestEnd = Math.max(latestEnd, end)
  }
  return false
}
