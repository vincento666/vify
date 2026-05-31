import type { WorkflowEdge, WorkflowNode } from '@/api/workflow'

export type WorkflowCanvasNodeType = 'START' | 'LLM' | 'CONDITION' | 'KNOWLEDGE' | 'API_CALL' | 'END'

export interface CanvasPosition {
  x: number
  y: number
}

export interface WorkflowCanvasNode extends WorkflowNode {
  type: WorkflowCanvasNodeType
  position: CanvasPosition
}

export interface WorkflowCanvasEdge extends WorkflowEdge {
  id: string
}

export interface WorkflowCanvasGraph {
  nodes: WorkflowCanvasNode[]
  edges: WorkflowCanvasEdge[]
}

const DEFAULT_POSITIONS: Record<'start' | 'end', CanvasPosition> = {
  start: { x: 120, y: 96 },
  end: { x: 780, y: 280 },
}

const NODE_LABELS: Record<WorkflowCanvasNodeType, string> = {
  START: '开始',
  LLM: '大模型',
  CONDITION: '条件',
  KNOWLEDGE: '知识库',
  API_CALL: 'API 调用',
  END: '结束',
}

const FIXED_NODE_KEYS = new Set(['start', 'end'])

function cloneConfig(config: Record<string, any> = {}) {
  return JSON.parse(JSON.stringify(config)) as Record<string, any>
}

function edgeId(sourceNodeKey: string, targetNodeKey: string) {
  return `${sourceNodeKey}->${targetNodeKey}`
}

function positionFromConfig(node: WorkflowNode, fallback: CanvasPosition) {
  const ui = (node.config as Record<string, any> | undefined)?.ui
  const position = ui?.position
  if (typeof position?.x === 'number' && typeof position?.y === 'number') {
    return { x: position.x, y: position.y }
  }
  return fallback
}

function withPositionInConfig(node: WorkflowCanvasNode): WorkflowNode {
  const config = cloneConfig(node.config)
  config.ui = {
    ...(config.ui || {}),
    position: { ...node.position },
  }
  return {
    nodeKey: node.nodeKey,
    type: node.type,
    name: node.name,
    config,
  }
}

export function createDefaultWorkflowGraph(): WorkflowCanvasGraph {
  return {
    nodes: [
      {
        nodeKey: 'start',
        type: 'START',
        name: NODE_LABELS.START,
        config: {
          outputVariables: ['USER_INPUT'],
          ui: { position: DEFAULT_POSITIONS.start },
        },
        position: DEFAULT_POSITIONS.start,
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: NODE_LABELS.END,
        config: {
          outputVariable: 'output',
          ui: { position: DEFAULT_POSITIONS.end },
        },
        position: DEFAULT_POSITIONS.end,
      },
    ],
    edges: [],
  }
}

export function createDefaultChatflowGraph(): WorkflowCanvasGraph {
  return {
    nodes: [
      {
        nodeKey: 'start',
        type: 'START',
        name: NODE_LABELS.START,
        config: {
          outputVariables: ['sys.query', 'sys.conversation_id', 'sys.user_id', 'sys.channel', 'sys.round'],
          ui: { position: DEFAULT_POSITIONS.start },
        },
        position: DEFAULT_POSITIONS.start,
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: NODE_LABELS.END,
        config: {
          outputVariable: 'output',
          ui: { position: DEFAULT_POSITIONS.end },
        },
        position: DEFAULT_POSITIONS.end,
      },
    ],
    edges: [{ id: edgeId('start', 'end'), sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
  }
}

export function hydrateWorkflowGraph(nodes: WorkflowNode[], edges: WorkflowEdge[]): WorkflowCanvasGraph {
  if (nodes.length === 0) return createDefaultWorkflowGraph()

  return {
    nodes: nodes.map((node, index) => ({
      ...node,
      type: node.type as WorkflowCanvasNodeType,
      config: cloneConfig(node.config),
      position: positionFromConfig(node, { x: 120 + index * 280, y: 96 + index * 120 }),
    })),
    edges: edges.map((edge) => ({
      ...edge,
      id: edgeId(edge.sourceNodeKey, edge.targetNodeKey),
    })),
  }
}

export function serializeWorkflowGraph(graph: WorkflowCanvasGraph): { nodes: WorkflowNode[]; edges: WorkflowEdge[] } {
  return {
    nodes: graph.nodes.map(withPositionInConfig),
    edges: graph.edges.map(({ sourceNodeKey, targetNodeKey, condition }) => ({
      sourceNodeKey,
      targetNodeKey,
      condition,
    })),
  }
}

export function addWorkflowNode(
  graph: WorkflowCanvasGraph,
  type: Exclude<WorkflowCanvasNodeType, 'START' | 'END'>,
  position: CanvasPosition,
): WorkflowCanvasGraph {
  const prefix = type.toLowerCase()
  const existing = new Set(graph.nodes.map((node) => node.nodeKey))
  let index = graph.nodes.filter((node) => node.type === type).length + 1
  let nodeKey = `${prefix}_${index}`
  while (existing.has(nodeKey)) {
    index += 1
    nodeKey = `${prefix}_${index}`
  }

  const node: WorkflowCanvasNode = {
    nodeKey,
    type,
    name: NODE_LABELS[type],
    config: {
      outputVariable: type === 'CONDITION' ? 'route' : 'output',
      ui: { position },
    },
    position,
  }

  return { nodes: [...graph.nodes, node], edges: graph.edges }
}

export function moveWorkflowNode(
  graph: WorkflowCanvasGraph,
  nodeKey: string,
  position: CanvasPosition,
): WorkflowCanvasGraph {
  return {
    nodes: graph.nodes.map((node) =>
      node.nodeKey === nodeKey
        ? { ...node, position, config: { ...cloneConfig(node.config), ui: { ...(node.config.ui || {}), position } } }
        : node,
    ),
    edges: graph.edges,
  }
}

export function connectWorkflowNodes(
  graph: WorkflowCanvasGraph,
  sourceNodeKey: string,
  targetNodeKey: string,
  condition: string | null = null,
): WorkflowCanvasGraph {
  if (sourceNodeKey === targetNodeKey) return graph
  const exists = graph.edges.some(
    (edge) => edge.sourceNodeKey === sourceNodeKey && edge.targetNodeKey === targetNodeKey,
  )
  if (exists) return graph

  return {
    nodes: graph.nodes,
    edges: [...graph.edges, { id: edgeId(sourceNodeKey, targetNodeKey), sourceNodeKey, targetNodeKey, condition }],
  }
}

export function deleteWorkflowNode(graph: WorkflowCanvasGraph, nodeKey: string): WorkflowCanvasGraph {
  if (FIXED_NODE_KEYS.has(nodeKey)) return graph
  return {
    nodes: graph.nodes.filter((node) => node.nodeKey !== nodeKey),
    edges: graph.edges.filter((edge) => edge.sourceNodeKey !== nodeKey && edge.targetNodeKey !== nodeKey),
  }
}

export function renameWorkflowNode(graph: WorkflowCanvasGraph, nodeKey: string, name: string): WorkflowCanvasGraph {
  return {
    nodes: graph.nodes.map((node) => (node.nodeKey === nodeKey ? { ...node, name } : node)),
    edges: graph.edges,
  }
}
