import type { WorkflowCanvasGraph, WorkflowCanvasNode } from './flowGraph'

export interface VariableCatalogItem {
  nodeKey: string
  variable: string
  label: string
  reference: string
}

export interface VariableCatalogGroup {
  title: string
  items: VariableCatalogItem[]
}

export function formatVariableReference(nodeKey: string, variable: string) {
  return `{{${nodeKey}.${variable}}}`
}

function outputVariables(node: WorkflowCanvasNode): string[] {
  if (node.type === 'START') {
    const values = node.config.outputVariables
    return Array.isArray(values) ? values.map(String) : ['USER_INPUT']
  }

  const outputVariable = node.config.outputVariable
  if (typeof outputVariable === 'string' && outputVariable.trim()) {
    return [outputVariable.trim()]
  }
  return []
}

function catalogItem(node: WorkflowCanvasNode, variable: string): VariableCatalogItem {
  return {
    nodeKey: node.nodeKey,
    variable,
    label: `${node.name}.${variable}`,
    reference: formatVariableReference(node.nodeKey, variable),
  }
}

function upstreamNodeKeys(graph: WorkflowCanvasGraph, selectedNodeKey: string) {
  const result: string[] = []
  const seen = new Set<string>([selectedNodeKey])
  const stack = [selectedNodeKey]

  while (stack.length > 0) {
    const target = stack.pop()!
    for (const edge of graph.edges.filter((item) => item.targetNodeKey === target)) {
      if (seen.has(edge.sourceNodeKey)) continue
      seen.add(edge.sourceNodeKey)
      result.push(edge.sourceNodeKey)
      stack.push(edge.sourceNodeKey)
    }
  }

  return result.reverse()
}

export function buildVariableCatalog(graph: WorkflowCanvasGraph, selectedNodeKey: string): VariableCatalogGroup[] {
  const nodesByKey = new Map(graph.nodes.map((node) => [node.nodeKey, node]))
  const start = nodesByKey.get('start')
  const startItems = start ? outputVariables(start).map((variable) => catalogItem(start, variable)) : []

  const upstreamItems = upstreamNodeKeys(graph, selectedNodeKey)
    .filter((nodeKey) => nodeKey !== 'start')
    .map((nodeKey) => nodesByKey.get(nodeKey))
    .filter((node): node is WorkflowCanvasNode => Boolean(node))
    .flatMap((node) => outputVariables(node).map((variable) => catalogItem(node, variable)))

  return [
    { title: '开始节点', items: startItems },
    { title: '上游节点', items: upstreamItems },
  ].filter((group) => group.items.length > 0)
}
