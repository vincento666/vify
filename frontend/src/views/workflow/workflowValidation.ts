import type { WorkflowCanvasGraph } from './flowGraph'

export interface WorkflowValidationResult {
  valid: boolean
  errors: string[]
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
  }

  return {
    valid: errors.length === 0,
    errors,
  }
}
