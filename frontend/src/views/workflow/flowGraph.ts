import type { WorkflowEdge, WorkflowNode } from '@/api/workflow'

export type WorkflowCanvasNodeType =
  | 'START'
  | 'LLM'
  | 'CONDITION'
  | 'KNOWLEDGE'
  | 'API_CALL'
  | 'TOOL_CALL'
  | 'EXECUTE_WORKFLOW'
  | 'AGENT_CALL'
  | 'TRANSFER_TO_HUMAN'
  | 'CODE'
  | 'TEXT_PROCESS'
  | 'JSON_PARSE'
  | 'VARIABLE_AGGREGATION'
  | 'VARIABLE_ASSIGN'
  | 'INTENT_RECOGNITION'
  | 'MESSAGE'
  | 'QUESTION'
  | 'HUMAN_INPUT'
  | 'INFORMATION_COLLECTION'
  | 'END'

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
  TOOL_CALL: '工具调用',
  EXECUTE_WORKFLOW: '工作流',
  AGENT_CALL: '智能体',
  TRANSFER_TO_HUMAN: '转人工',
  CODE: '代码',
  TEXT_PROCESS: '文本处理',
  JSON_PARSE: 'JSON 解析',
  VARIABLE_AGGREGATION: '变量聚合',
  VARIABLE_ASSIGN: '变量赋值',
  INTENT_RECOGNITION: '意图识别',
  MESSAGE: '消息',
  QUESTION: '问题',
  HUMAN_INPUT: '人工输入',
  INFORMATION_COLLECTION: '信息收集',
  END: '结束',
}

const FIXED_NODE_KEYS = new Set(['start', 'end'])
const AUTO_LAYOUT = {
  x: 120,
  y: 96,
  columnGap: 520,
  rowGap: 180,
}

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
          outputVariables: ['USER_INPUT', 'CONVERSATION_NAME'],
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
    config: defaultNodeConfig(type, position),
    position,
  }

  return { nodes: [...graph.nodes, node], edges: graph.edges }
}

function defaultNodeConfig(type: Exclude<WorkflowCanvasNodeType, 'START' | 'END'>, position: CanvasPosition) {
  const base = {
    outputVariable: type === 'CONDITION' ? 'route' : 'output',
    ui: { position },
  }
  if (type === 'CODE') {
    return {
      ...base,
      language: 'python',
      code: "result = {'output': inputs.get('USER_INPUT', '')}",
      outputParameters: [{ name: 'output', type: 'string' }],
    }
  }
  if (type === 'TOOL_CALL') {
    return {
      ...base,
      outputVariable: 'result',
      resourceType: 'MCP_TOOL',
      resourceId: '',
      toolName: '',
      serverIds: [],
      inputMappings: [],
      timeoutMs: 30000,
      retryCount: 0,
      errorBehavior: 'fail',
      outputParameters: [
        { name: 'result', type: 'string' },
        { name: 'success', type: 'boolean' },
        { name: 'evidence', type: 'object' },
      ],
    }
  }
  if (type === 'EXECUTE_WORKFLOW') {
    return {
      ...base,
      outputVariable: 'status',
      resourceType: 'SUBWORKFLOW',
      targetWorkflowId: '',
      inputMappings: [],
      outputMappings: [],
      timeoutMs: 30000,
      maxDepth: 3,
      outputParameters: [
        { name: 'nestedRunId', type: 'number' },
        { name: 'status', type: 'string' },
        { name: 'error', type: 'string' },
      ],
    }
  }
  if (type === 'AGENT_CALL') {
    return {
      ...base,
      outputVariable: 'answer',
      resourceType: 'AGENT',
      targetAgentId: '',
      resourceId: '',
      inputMappings: [],
      messageTemplate: '{{start.USER_INPUT}}',
      historyMode: 'none',
      outputMappings: [],
      timeoutMs: 30000,
      maxDepth: 3,
      outputParameters: [
        { name: 'answer', type: 'string' },
        { name: 'sessionId', type: 'number' },
        { name: 'status', type: 'string' },
        { name: 'latencyMs', type: 'number' },
        { name: 'mappedInputSummary', type: 'object' },
        { name: 'mappedOutputSummary', type: 'object' },
        { name: 'toolCalls', type: 'array' },
        { name: 'error', type: 'string' },
      ],
    }
  }
  if (type === 'TRANSFER_TO_HUMAN') {
    return {
      ...base,
      outputVariable: 'handoff_status',
      message: '已为你转接人工客服，请稍候。',
      queue: 'general',
      reason: 'user_request',
      priority: 'normal',
      slaMinutes: 30,
      outputParameters: [
        { name: 'handoff_id', type: 'number' },
        { name: 'handoff_status', type: 'string' },
        { name: 'queue', type: 'string' },
        { name: 'priority', type: 'string' },
      ],
    }
  }
  if (type === 'TEXT_PROCESS') {
    return {
      ...base,
      operation: 'format_template',
      template: '{{start.USER_INPUT}}',
      outputParameters: [{ name: 'text', type: 'string' }],
    }
  }
  if (type === 'JSON_PARSE') {
    return {
      ...base,
      outputVariable: 'parsed',
      source: '{{start.USER_INPUT}}',
      outputParameters: [{ name: 'parsed', type: 'object' }],
    }
  }
  if (type === 'VARIABLE_AGGREGATION') {
    return {
      ...base,
      outputVariable: 'aggregate',
      strategy: 'first_non_empty',
      sources: [{ name: 'source_1', value: '{{start.USER_INPUT}}' }],
      defaultValue: '',
      outputParameters: [{ name: 'aggregate', type: 'string' }],
    }
  }
  if (type === 'VARIABLE_ASSIGN') {
    return {
      ...base,
      outputVariable: 'assigned',
      targetScope: 'flow',
      targetVariable: 'value',
      source: '{{start.USER_INPUT}}',
      writeMode: 'set',
      outputParameters: [{ name: 'assigned', type: 'string' }],
    }
  }
  if (type === 'INTENT_RECOGNITION') {
    return {
      ...base,
      outputVariable: 'intent',
      inputSource: '{{start.sys.query}}',
      classifierMode: 'fake',
      defaultIntent: 'default',
      includeHistory: false,
      intents: [
        { key: 'default', name: '默认', description: '未识别到明确意图', examples: [] },
      ],
      outputParameters: [
        { name: 'intent', type: 'string' },
        { name: 'confidence', type: 'number' },
        { name: 'reason', type: 'string' },
      ],
    }
  }
  if (type === 'MESSAGE') {
    return {
      ...base,
      outputVariable: 'content',
      content: '{{start.sys.query}}',
      streamOutput: 'inherit',
      streamTarget: 'message',
      fallbackMode: 'aggregate',
      outputParameters: [{ name: 'content', type: 'string' }],
    }
  }
  if (type === 'QUESTION') {
    return {
      ...base,
      outputVariable: 'answer',
      question: '请补充你的问题',
      answerType: 'text',
      options: [],
      timeoutSeconds: 0,
      outputParameters: [{ name: 'answer', type: 'string' }],
    }
  }
  if (type === 'HUMAN_INPUT') {
    return {
      ...base,
      outputVariable: 'payload',
      prompt: '请人工处理',
      inputSchema: '[]',
      approvalMode: 'input',
      assigneeRole: '',
      outputParameters: [{ name: 'payload', type: 'object' }],
    }
  }
  if (type === 'INFORMATION_COLLECTION') {
    return {
      ...base,
      outputVariable: 'profile',
      inputSource: '{{start.sys.query}}',
      collectionKey: 'profile',
      includeHistory: false,
      extractorMode: 'fake',
      maxRounds: 3,
      streamOutput: 'enabled',
      fields: [
        { name: 'name', type: 'string', required: true, description: '姓名' },
        { name: 'phone', type: 'string', required: true, description: '手机号' },
      ],
      outputParameters: [
        { name: 'profile', type: 'object' },
        { name: 'complete', type: 'boolean' },
        { name: 'missing', type: 'array' },
      ],
    }
  }
  return base
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

export function autoLayoutWorkflowGraph(graph: WorkflowCanvasGraph): WorkflowCanvasGraph {
  const originalOrder = new Map(graph.nodes.map((node, index) => [node.nodeKey, index]))
  const layerByKey = new Map<string, number>()
  const startNode = graph.nodes.find((node) => node.nodeKey === 'start' || node.type === 'START')
  if (startNode) layerByKey.set(startNode.nodeKey, 0)

  const orderedEdges = [...graph.edges].sort((left, right) => {
    const leftSource = originalOrder.get(left.sourceNodeKey) ?? Number.MAX_SAFE_INTEGER
    const rightSource = originalOrder.get(right.sourceNodeKey) ?? Number.MAX_SAFE_INTEGER
    if (leftSource !== rightSource) return leftSource - rightSource
    return (originalOrder.get(left.targetNodeKey) ?? 0) - (originalOrder.get(right.targetNodeKey) ?? 0)
  })

  for (let iteration = 0; iteration < graph.nodes.length; iteration += 1) {
    let changed = false
    for (const edge of orderedEdges) {
      const sourceLayer = layerByKey.get(edge.sourceNodeKey)
      if (sourceLayer === undefined) continue
      const nextLayer = sourceLayer + 1
      if ((layerByKey.get(edge.targetNodeKey) ?? -1) < nextLayer) {
        layerByKey.set(edge.targetNodeKey, nextLayer)
        changed = true
      }
    }
    if (!changed) break
  }

  for (const node of graph.nodes) {
    if (layerByKey.has(node.nodeKey)) continue
    const currentMaxLayer = Math.max(0, ...layerByKey.values())
    layerByKey.set(node.nodeKey, node.type === 'END' ? currentMaxLayer + 1 : Math.max(1, currentMaxLayer))
  }

  const nodesByLayer = new Map<number, WorkflowCanvasNode[]>()
  for (const node of graph.nodes) {
    const layer = layerByKey.get(node.nodeKey) ?? 0
    nodesByLayer.set(layer, [...(nodesByLayer.get(layer) || []), node])
  }

  const orderedLayers = [...nodesByLayer.keys()].sort((left, right) => left - right)
  const positions = new Map<string, CanvasPosition>()
  for (const layer of orderedLayers) {
    const layerNodes = [...(nodesByLayer.get(layer) || [])].sort(
      (left, right) => (originalOrder.get(left.nodeKey) ?? 0) - (originalOrder.get(right.nodeKey) ?? 0),
    )
    layerNodes.forEach((node, index) => {
      positions.set(node.nodeKey, {
        x: AUTO_LAYOUT.x + layer * AUTO_LAYOUT.columnGap,
        y: AUTO_LAYOUT.y + index * AUTO_LAYOUT.rowGap,
      })
    })
  }

  return {
    nodes: graph.nodes.map((node) => {
      const position = positions.get(node.nodeKey) || node.position
      return {
        ...node,
        position,
        config: {
          ...cloneConfig(node.config),
          ui: {
            ...(node.config.ui || {}),
            position,
          },
        },
      }
    }),
    edges: graph.edges.map((edge) => ({ ...edge })),
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

export function deleteWorkflowEdge(graph: WorkflowCanvasGraph, edgeIdToDelete: string): WorkflowCanvasGraph {
  return {
    nodes: graph.nodes,
    edges: graph.edges.filter((edge) => edge.id !== edgeIdToDelete),
  }
}

export function insertWorkflowNodeOnEdge(
  graph: WorkflowCanvasGraph,
  type: Exclude<WorkflowCanvasNodeType, 'START' | 'END'>,
  edgeIdToSplit: string,
  position: CanvasPosition,
): WorkflowCanvasGraph {
  const edgeToSplit = graph.edges.find((edge) => edge.id === edgeIdToSplit)
  if (!edgeToSplit) return graph

  const graphWithNode = addWorkflowNode(graph, type, position)
  const insertedNode = graphWithNode.nodes[graphWithNode.nodes.length - 1]
  if (!insertedNode) return graph

  const withoutOriginalEdge: WorkflowCanvasGraph = {
    nodes: graphWithNode.nodes,
    edges: graphWithNode.edges.filter((edge) => edge.id !== edgeIdToSplit),
  }

  return connectWorkflowNodes(
    connectWorkflowNodes(withoutOriginalEdge, edgeToSplit.sourceNodeKey, insertedNode.nodeKey, edgeToSplit.condition),
    insertedNode.nodeKey,
    edgeToSplit.targetNodeKey,
  )
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
