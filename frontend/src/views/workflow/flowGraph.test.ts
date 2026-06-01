import { describe, expect, it } from 'vitest'

import {
  addWorkflowNode,
  autoLayoutWorkflowGraph,
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
})
