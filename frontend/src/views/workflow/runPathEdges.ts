export type RunPathEdgeLike = {
  id: string
  sourceNodeKey: string
  targetNodeKey: string
  condition?: string | null
}

export type RunPathNodeDetailLike = {
  nodeKey?: string
  status?: string
  outputs?: Record<string, unknown>
}

export type RunPathEdgeClass =
  | 'edge-running'
  | 'edge-succeeded'
  | 'edge-active-branch'
  | 'edge-inactive-branch'

export function deriveRunPathEdgeClasses(
  edges: RunPathEdgeLike[],
  nodeDetails: RunPathNodeDetailLike[],
): Map<string, RunPathEdgeClass[]> {
  const classes = new Map<string, Set<RunPathEdgeClass>>()
  const detailByNodeKey = new Map(
    nodeDetails
      .map((detail) => [String(detail.nodeKey || ''), detail] as const)
      .filter(([nodeKey]) => Boolean(nodeKey)),
  )

  for (const edge of edges) {
    const targetStatus = normalizeRunStatus(detailByNodeKey.get(edge.targetNodeKey)?.status)
    if (['RUNNING', 'INTERRUPTED', 'PENDING', 'WAITING'].includes(targetStatus)) addEdgeClass(classes, edge.id, 'edge-running')
    if (['SUCCEEDED', 'COMPLETED'].includes(targetStatus)) addEdgeClass(classes, edge.id, 'edge-succeeded')
  }

  for (const detail of nodeDetails) {
    const sourceNodeKey = String(detail.nodeKey || '')
    const activeBranchValue = extractActiveBranchValue(detail.outputs)
    if (!sourceNodeKey || activeBranchValue === null) continue

    const outgoingEdges = edges.filter((edge) => edge.sourceNodeKey === sourceNodeKey)
    if (outgoingEdges.length <= 1) continue

    const matchedEdges = outgoingEdges.filter((edge) => edgeMatchesBranch(edge, activeBranchValue))
    const activeEdgeIds = new Set(matchedEdges.map((edge) => edge.id))
    if (!activeEdgeIds.size) continue

    for (const edge of outgoingEdges) {
      if (activeEdgeIds.has(edge.id)) {
        addEdgeClass(classes, edge.id, 'edge-active-branch')
      } else {
        addEdgeClass(classes, edge.id, 'edge-inactive-branch')
      }
    }
  }

  return new Map(
    Array.from(classes.entries()).map(([edgeId, edgeClasses]) => [edgeId, Array.from(edgeClasses)]),
  )
}

function normalizeRunStatus(status: unknown) {
  return String(status || '').trim().toUpperCase()
}

function addEdgeClass(
  classes: Map<string, Set<RunPathEdgeClass>>,
  edgeId: string,
  edgeClass: RunPathEdgeClass,
) {
  const current = classes.get(edgeId) || new Set<RunPathEdgeClass>()
  current.add(edgeClass)
  classes.set(edgeId, current)
}

function edgeMatchesBranch(edge: RunPathEdgeLike, branchValue: string) {
  const condition = edge.condition
  if (condition === null || condition === undefined || condition === '') return branchValue === 'default'
  return String(condition) === branchValue
}

function extractActiveBranchValue(outputs: Record<string, unknown> | undefined): string | null {
  if (!outputs) return null
  for (const key of ['route', 'branch', 'intent', 'selectedBranch', 'activeBranch']) {
    const value = scalarOutputValue(outputs[key])
    if (value !== null) return value
  }
  const scalarEntries = Object.values(outputs)
    .map(scalarOutputValue)
    .filter((value): value is string => value !== null)
  return scalarEntries.length === 1 ? scalarEntries[0] : null
}

function scalarOutputValue(value: unknown): string | null {
  if (typeof value === 'string' && value.trim()) return value.trim()
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return null
}
