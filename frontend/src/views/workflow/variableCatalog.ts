import type { WorkflowCanvasGraph, WorkflowCanvasNode } from './flowGraph'
import { normalizeInputConfig, normalizeOutputConfig, normalizeStartVariables, type OutputParameterType } from './nodeConfig'

export type VariableCatalogScope = 'user' | 'global' | 'system' | 'conversation' | 'upstream' | 'local'
export type VariableCatalogType = OutputParameterType | 'file'

export interface VariableCatalogItem {
  nodeKey: string
  variable: string
  label: string
  reference: string
  type: VariableCatalogType
}

export interface VariableCatalogGroup {
  title: string
  scope: VariableCatalogScope
  sourceKey: string
  sourceLabel: string
  sourceNodeKey?: string
  items: VariableCatalogItem[]
}

export interface VariableDefinition {
  name: string
  type: VariableCatalogType
}

interface BuildVariableCatalogOptions {
  flowType?: 'WORKFLOW' | 'CHATFLOW'
  globalVariables?: Partial<Record<'user' | 'app' | 'system' | 'conversation', VariableDefinition[]>>
}

export function formatVariableReference(nodeKey: string, variable: string) {
  return `{{${nodeKey}.${variable}}}`
}

export function formatLocalVariableReference(variable: string) {
  return `{{${variable}}}`
}

function outputVariables(node: WorkflowCanvasNode): VariableDefinition[] {
  if (node.type === 'START') {
    return normalizeStartVariables(node.config).map((variable) => ({ name: variable.name, type: variable.type }))
  }

  const outputVariable = node.config.outputVariable
  const normalizedOutputParameters = normalizeOutputConfig(node.config).parameters
  if (normalizedOutputParameters.length > 0) {
    return normalizedOutputParameters.map((item) => ({ name: item.name, type: item.type }))
  }
  if (typeof outputVariable === 'string' && outputVariable.trim()) {
    return [{ name: outputVariable.trim(), type: 'string' }]
  }
  return []
}

function catalogItem(node: WorkflowCanvasNode, variable: VariableDefinition): VariableCatalogItem {
  return {
    nodeKey: node.nodeKey,
    variable: variable.name,
    label: variable.name,
    reference: formatVariableReference(node.nodeKey, variable.name),
    type: variable.type,
  }
}

function staticCatalogItem(scopeKey: string, variable: VariableDefinition): VariableCatalogItem {
  return {
    nodeKey: scopeKey,
    variable: variable.name,
    label: variable.name,
    reference: formatVariableReference(scopeKey, variable.name),
    type: variable.type,
  }
}

function localCatalogItem(node: WorkflowCanvasNode, variable: VariableDefinition): VariableCatalogItem {
  return {
    nodeKey: node.nodeKey,
    variable: variable.name,
    label: variable.name,
    reference: formatLocalVariableReference(variable.name),
    type: variable.type,
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

function configuredGlobalScopeGroups(options: BuildVariableCatalogOptions): VariableCatalogGroup[] {
  const definitions = options.globalVariables ?? {}
  const groups: Array<{
    key: 'user' | 'global' | 'sys' | 'conversation'
    title: string
    scope: VariableCatalogScope
    variables?: VariableDefinition[]
  }> = [
    { key: 'conversation', title: '会话变量', scope: 'conversation', variables: definitions.conversation },
    { key: 'user', title: '用户变量', scope: 'user', variables: definitions.user },
    { key: 'global', title: '应用变量', scope: 'global', variables: definitions.app },
    { key: 'sys', title: '系统变量', scope: 'system', variables: definitions.system },
  ]

  return groups
    .map((group) => ({
      title: group.title,
      scope: group.scope,
      sourceKey: group.key,
      sourceLabel: group.title,
      items: (group.variables ?? [])
        .filter((variable) => String(variable.name || '').trim().length > 0)
        .map((variable) => staticCatalogItem(group.key, variable)),
    }))
    .filter((group) => group.items.length > 0)
}

export function buildVariableCatalog(
  graph: WorkflowCanvasGraph,
  selectedNodeKey: string,
  options: BuildVariableCatalogOptions = {},
): VariableCatalogGroup[] {
  const nodesByKey = new Map(graph.nodes.map((node) => [node.nodeKey, node]))
  const upstreamGroups = upstreamNodeKeys(graph, selectedNodeKey)
    .map((nodeKey) => nodesByKey.get(nodeKey))
    .filter((node): node is WorkflowCanvasNode => Boolean(node))
    .map((node) => ({
      title: node.name,
      scope: 'upstream' as const,
      sourceKey: node.nodeKey,
      sourceLabel: node.name,
      sourceNodeKey: node.nodeKey,
      items: outputVariables(node).map((variable) => catalogItem(node, variable)),
    }))
    .filter((group) => group.items.length > 0)
  return [...configuredGlobalScopeGroups(options), ...upstreamGroups]
}

export function buildLocalVariableCatalog(graph: WorkflowCanvasGraph, selectedNodeKey: string): VariableCatalogGroup[] {
  const node = graph.nodes.find((item) => item.nodeKey === selectedNodeKey)
  if (!node) return []

  if (node.type === 'END') {
    const outputItems = normalizeOutputConfig(node.config, { respectExplicitEmpty: true }).parameters.map((variable) => localCatalogItem(node, variable))
    return outputItems.length > 0
      ? [{
        title: '输出',
        scope: 'local',
        sourceKey: node.nodeKey,
        sourceLabel: node.name,
        sourceNodeKey: node.nodeKey,
        items: outputItems,
      }]
      : []
  }

  const inputItems = normalizeInputConfig(node.config).parameters.map((variable) => localCatalogItem(node, variable))
  return inputItems.length > 0
    ? [{
      title: '输入',
      scope: 'local',
      sourceKey: node.nodeKey,
      sourceLabel: node.name,
      sourceNodeKey: node.nodeKey,
      items: inputItems,
    }]
    : []
}

export function buildInlineVariableCatalog(
  graph: WorkflowCanvasGraph,
  selectedNodeKey: string,
  _options: BuildVariableCatalogOptions = {},
): VariableCatalogGroup[] {
  const node = graph.nodes.find((item) => item.nodeKey === selectedNodeKey)
  if (!node) return []

  if (node.type === 'END') {
    return buildLocalVariableCatalog(graph, selectedNodeKey)
  }

  return buildLocalVariableCatalog(graph, selectedNodeKey)
}
