import { describe, expect, it } from 'vitest'

import {
  addWorkflowNode,
  connectWorkflowNodes,
  createDefaultChatflowGraph,
  createDefaultWorkflowGraph,
  deleteWorkflowNode,
  hydrateWorkflowGraph,
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

    expect(deleted.nodes.map((node) => node.nodeKey)).not.toContain(conditionKey)
    expect(deleted.edges.some((edge) => edge.sourceNodeKey === conditionKey || edge.targetNodeKey === conditionKey)).toBe(false)
    expect(fixedStart.nodes.map((node) => node.nodeKey)).toContain('start')
  })

  it('creates default Chatflow START variables for conversational context', () => {
    const graph = createDefaultChatflowGraph()
    const start = graph.nodes.find((node) => node.nodeKey === 'start')

    expect(start?.config.outputVariables).toEqual([
      'sys.query',
      'sys.conversation_id',
      'sys.user_id',
      'sys.channel',
      'sys.round',
    ])
  })
})
