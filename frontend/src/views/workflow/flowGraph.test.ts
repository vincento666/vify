import { describe, expect, it } from 'vitest'

import {
  addWorkflowNode,
  autoLayoutWorkflowGraph,
  connectWorkflowNodes,
  createDefaultChatflowGraph,
  createDefaultWorkflowGraph,
  deleteWorkflowEdge,
  deleteWorkflowNode,
  hydrateWorkflowGraph,
  insertWorkflowNodeOnEdge,
  moveWorkflowNode,
  serializeWorkflowGraph,
} from './flowGraph'

describe('workflow canvas graph model', () => {
  it('serializes and rehydrates a saved canvas graph with positions and edges', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'LLM', { x: 520, y: 260 })
    const llmKey = graph.nodes.find((node) => node.type === 'LLM')?.nodeKey

    expect(llmKey).toMatch(/^llm_/)

    graph = connectWorkflowNodes(graph, 'start', llmKey!)
    graph = connectWorkflowNodes(graph, llmKey!, 'end')
    graph = moveWorkflowNode(graph, llmKey!, { x: 640, y: 320 })

    const saved = serializeWorkflowGraph(graph)
    const reopened = hydrateWorkflowGraph(saved.nodes, saved.edges)

    expect(saved.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          nodeKey: llmKey,
          type: 'LLM',
          config: expect.objectContaining({
            ui: { position: { x: 640, y: 320 } },
          }),
        }),
      ]),
    )
    expect(reopened.nodes.find((node) => node.nodeKey === llmKey)?.position).toEqual({ x: 640, y: 320 })
    expect(reopened.edges).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ sourceNodeKey: 'start', targetNodeKey: llmKey }),
        expect.objectContaining({ sourceNodeKey: llmKey, targetNodeKey: 'end' }),
      ]),
    )
  })

  it('deletes a canvas node and removes incident edges while preserving fixed nodes', () => {
    let graph = addWorkflowNode(createDefaultWorkflowGraph(), 'CONDITION', { x: 520, y: 260 })
    const conditionKey = graph.nodes.find((node) => node.type === 'CONDITION')!.nodeKey
    graph = connectWorkflowNodes(connectWorkflowNodes(graph, 'start', conditionKey), conditionKey, 'end')

    const deleted = deleteWorkflowNode(graph, conditionKey)
    const fixedStart = deleteWorkflowNode(deleted, 'start')
    const fixedEnd = deleteWorkflowNode(deleted, 'end')

    expect(deleted.nodes.map((node) => node.nodeKey)).not.toContain(conditionKey)
    expect(deleted.edges.some((edge) => edge.sourceNodeKey === conditionKey || edge.targetNodeKey === conditionKey)).toBe(false)
    expect(fixedStart.nodes.map((node) => node.nodeKey)).toContain('start')
    expect(fixedEnd.nodes.map((node) => node.nodeKey)).toContain('end')
  })

  it('deletes a selected edge without removing its nodes', () => {
    const graph = createDefaultChatflowGraph()
    const deleted = deleteWorkflowEdge(graph, 'start->end')

    expect(deleted.nodes.map((node) => node.nodeKey)).toEqual(['start', 'end'])
    expect(deleted.edges).toEqual([])
  })

  it('inserts a node on an existing edge and reconnects through the new node', () => {
    const graph = createDefaultChatflowGraph()
    const inserted = insertWorkflowNodeOnEdge(graph, 'LLM', 'start->end', { x: 420, y: 180 })

    expect(inserted.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ nodeKey: 'llm_1', type: 'LLM', position: { x: 420, y: 180 } }),
      ]),
    )
    expect(inserted.edges).toEqual([
      expect.objectContaining({ sourceNodeKey: 'start', targetNodeKey: 'llm_1' }),
      expect.objectContaining({ sourceNodeKey: 'llm_1', targetNodeKey: 'end' }),
    ])
  })

  it('preserves a condition branch when inserting a node on a conditional edge', () => {
    let graph = createDefaultChatflowGraph()
    graph = addWorkflowNode(graph, 'INTENT_RECOGNITION', { x: 420, y: 180 })
    graph = addWorkflowNode(graph, 'MESSAGE', { x: 760, y: 120 })
    graph = {
      nodes: graph.nodes,
      edges: [
        { id: 'start->intent_recognition_1', sourceNodeKey: 'start', targetNodeKey: 'intent_recognition_1', condition: null },
        { id: 'intent_recognition_1->message_1', sourceNodeKey: 'intent_recognition_1', targetNodeKey: 'message_1', condition: 'refund' },
      ],
    }

    const inserted = insertWorkflowNodeOnEdge(graph, 'LLM', 'intent_recognition_1->message_1', { x: 600, y: 150 })

    expect(inserted.edges).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          sourceNodeKey: 'intent_recognition_1',
          targetNodeKey: 'llm_1',
          condition: 'refund',
        }),
        expect.objectContaining({
          sourceNodeKey: 'llm_1',
          targetNodeKey: 'message_1',
          condition: null,
        }),
      ]),
    )
    expect(inserted.edges.some((edge) => edge.id === 'intent_recognition_1->message_1')).toBe(false)
  })

  it('creates Coze-like default Chatflow START variables for conversational context', () => {
    const graph = createDefaultChatflowGraph()
    const start = graph.nodes.find((node) => node.nodeKey === 'start')

    expect(start?.config.outputVariables).toEqual([
      'sys.query',
      'sys.conversation_id',
      'sys.user_id',
      'sys.channel',
      'sys.channel_id',
    ])
  })

  it('auto-layouts nodes into deterministic columns while preserving configs and conditional edges', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'CONDITION', { x: 10, y: 10 })
    graph = addWorkflowNode(graph, 'LLM', { x: 20, y: 20 })

    graph = {
      ...graph,
      nodes: graph.nodes.map((node) =>
        node.nodeKey === 'llm_1'
          ? {
            ...node,
            config: {
              ...node.config,
              prompt: 'keep this prompt',
              outputVariable: 'answer',
            },
          }
          : node,
      ),
    }
    graph = connectWorkflowNodes(graph, 'start', 'condition_1')
    graph = connectWorkflowNodes(graph, 'condition_1', 'llm_1', 'yes')
    graph = connectWorkflowNodes(graph, 'condition_1', 'end')
    graph = connectWorkflowNodes(graph, 'llm_1', 'end')

    const laidOut = autoLayoutWorkflowGraph(graph)
    const byKey = new Map(laidOut.nodes.map((node) => [node.nodeKey, node]))

    expect(byKey.get('start')?.position).toEqual({ x: 120, y: 96 })
    expect(byKey.get('condition_1')?.position.x).toBeGreaterThan(byKey.get('start')!.position.x)
    expect(byKey.get('llm_1')?.position.x).toBeGreaterThan(byKey.get('condition_1')!.position.x)
    expect(byKey.get('end')?.position.x).toBeGreaterThan(byKey.get('llm_1')!.position.x)
    expect(byKey.get('llm_1')?.config.prompt).toBe('keep this prompt')
    expect(byKey.get('llm_1')?.config.ui.position).toEqual(byKey.get('llm_1')?.position)
    expect(laidOut.edges).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          sourceNodeKey: 'condition_1',
          targetNodeKey: 'llm_1',
          condition: 'yes',
        }),
      ]),
    )
  })

  it('adds runtime-backed data transform nodes with Coze-aligned labels', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'CODE', { x: 520, y: 120 })
    graph = addWorkflowNode(graph, 'TEXT_PROCESS', { x: 520, y: 320 })
    graph = addWorkflowNode(graph, 'JSON_PARSE', { x: 520, y: 520 })

    expect(graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ nodeKey: 'code_1', type: 'CODE', name: '代码' }),
        expect.objectContaining({ nodeKey: 'text_process_1', type: 'TEXT_PROCESS', name: '文本处理' }),
        expect.objectContaining({ nodeKey: 'json_parse_1', type: 'JSON_PARSE', name: 'JSON 解析' }),
      ]),
    )
  })

  it('adds variable aggregation and assignment as separate runtime-backed nodes', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'VARIABLE_AGGREGATION', { x: 520, y: 120 })
    graph = addWorkflowNode(graph, 'VARIABLE_ASSIGN', { x: 520, y: 320 })

    expect(graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ nodeKey: 'variable_aggregation_1', type: 'VARIABLE_AGGREGATION', name: '变量聚合' }),
        expect.objectContaining({
          nodeKey: 'variable_assign_1',
          type: 'VARIABLE_ASSIGN',
          name: '变量赋值',
          config: expect.objectContaining({ targetScope: 'flow', targetVariable: '' }),
        }),
      ]),
    )
  })

  it('adds intent recognition as a separate semantic branch node', () => {
    const graph = addWorkflowNode(createDefaultChatflowGraph(), 'INTENT_RECOGNITION', { x: 520, y: 120 })

    expect(graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ nodeKey: 'intent_recognition_1', type: 'INTENT_RECOGNITION', name: '意图识别' }),
      ]),
    )
  })

  it('adds Chatflow message/question/human input nodes with separate labels', () => {
    let graph = createDefaultChatflowGraph()
    graph = addWorkflowNode(graph, 'MESSAGE', { x: 520, y: 120 })
    graph = addWorkflowNode(graph, 'QUESTION', { x: 520, y: 320 })
    graph = addWorkflowNode(graph, 'HUMAN_INPUT', { x: 520, y: 520 })

    expect(graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ nodeKey: 'message_1', type: 'MESSAGE', name: '消息' }),
        expect.objectContaining({ nodeKey: 'question_1', type: 'QUESTION', name: '问题' }),
        expect.objectContaining({ nodeKey: 'human_input_1', type: 'HUMAN_INPUT', name: '人工输入' }),
      ]),
    )
  })

  it('adds Chatflow information collection as a distinct slot filling node', () => {
    const graph = addWorkflowNode(createDefaultChatflowGraph(), 'INFORMATION_COLLECTION', { x: 520, y: 120 })

    expect(graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ nodeKey: 'information_collection_1', type: 'INFORMATION_COLLECTION', name: '信息收集' }),
      ]),
    )
  })

  it('adds tool call as an explicit runtime-backed resource node', () => {
    const graph = addWorkflowNode(createDefaultWorkflowGraph(), 'TOOL_CALL', { x: 520, y: 120 })

    expect(graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          nodeKey: 'tool_call_1',
          type: 'TOOL_CALL',
          name: '工具调用',
          config: expect.objectContaining({
            resourceType: 'MCP_TOOL',
            toolName: '',
            inputMappings: [],
            outputParameters: expect.arrayContaining([
              expect.objectContaining({ name: 'result', type: 'string' }),
              expect.objectContaining({ name: 'evidence', type: 'object' }),
            ]),
          }),
        }),
      ]),
    )
  })

  it('uses official knowledge retrieval naming for the knowledge node', () => {
    const graph = addWorkflowNode(createDefaultWorkflowGraph(), 'KNOWLEDGE', { x: 520, y: 120 })

    expect(graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ nodeKey: 'knowledge_1', type: 'KNOWLEDGE', name: '知识检索' }),
      ]),
    )
  })

  it('adds execute workflow as an explicit published subworkflow node', () => {
    const graph = addWorkflowNode(createDefaultWorkflowGraph(), 'EXECUTE_WORKFLOW', { x: 520, y: 120 })

    expect(graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          nodeKey: 'execute_workflow_1',
          type: 'EXECUTE_WORKFLOW',
          name: '工作流',
          config: expect.objectContaining({
            targetWorkflowId: '',
            inputMappings: [],
            outputMappings: [],
            timeoutMs: 30000,
            maxDepth: 3,
            outputParameters: expect.arrayContaining([
              expect.objectContaining({ name: 'nestedRunId', type: 'number' }),
              expect.objectContaining({ name: 'status', type: 'string' }),
              expect.objectContaining({ name: 'error', type: 'string' }),
            ]),
          }),
        }),
      ]),
    )
  })

  it('adds agent call as an explicit runtime-backed Agent resource node', () => {
    const graph = addWorkflowNode(createDefaultChatflowGraph(), 'AGENT_CALL', { x: 520, y: 120 })

    expect(graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          nodeKey: 'agent_call_1',
          type: 'AGENT_CALL',
          name: '智能体',
          config: expect.objectContaining({
            resourceType: 'AGENT',
            targetAgentId: '',
            inputMappings: [],
            historyMode: 'none',
            outputMappings: [],
            timeoutMs: 30000,
            maxDepth: 3,
            outputParameters: expect.arrayContaining([
              expect.objectContaining({ name: 'answer', type: 'string' }),
              expect.objectContaining({ name: 'sessionId', type: 'number' }),
              expect.objectContaining({ name: 'status', type: 'string' }),
              expect.objectContaining({ name: 'toolCalls', type: 'array' }),
            ]),
          }),
        }),
      ]),
    )
  })

  it('adds transfer to human as a Chatflow-only handoff node with ticket outputs', () => {
    const graph = addWorkflowNode(createDefaultChatflowGraph(), 'TRANSFER_TO_HUMAN', { x: 520, y: 120 })

    expect(graph.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          nodeKey: 'transfer_to_human_1',
          type: 'TRANSFER_TO_HUMAN',
          name: '转人工',
          config: expect.objectContaining({
            message: '已为你转接人工客服，请稍候。',
            queue: 'general',
            priority: 'normal',
            slaMinutes: 30,
            outputParameters: expect.arrayContaining([
              expect.objectContaining({ name: 'handoff_id', type: 'number' }),
              expect.objectContaining({ name: 'handoff_status', type: 'string' }),
              expect.objectContaining({ name: 'queue', type: 'string' }),
            ]),
          }),
        }),
      ]),
    )
  })
})
