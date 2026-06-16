import { describe, expect, it } from 'vitest'

import { addWorkflowNode, connectWorkflowNodes, createDefaultWorkflowGraph, deleteWorkflowNode } from './flowGraph'
import { validateWorkflowGraph } from './workflowValidation'

describe('workflow graph validation', () => {
  it('requires a reachable path from START to END', () => {
    const graph = createDefaultWorkflowGraph()

    expect(validateWorkflowGraph(graph)).toEqual(
      expect.objectContaining({
        valid: false,
        errors: expect.arrayContaining(['START must connect to END through at least one path']),
      }),
    )

    expect(validateWorkflowGraph(connectWorkflowNodes(graph, 'start', 'end')).valid).toBe(true)
  })

  it('rejects disconnected non-fixed nodes before test run or publish', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'LLM', { x: 320, y: 240 })
    graph = connectWorkflowNodes(graph, 'start', 'end')

    expect(validateWorkflowGraph(graph)).toEqual(
      expect.objectContaining({
        valid: false,
        errors: expect.arrayContaining(['Node llm_1 is not connected']),
      }),
    )
  })

  it('requires LLM nodes to select a concrete model before running', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'LLM', { x: 320, y: 240 })
    graph = connectWorkflowNodes(graph, 'start', 'llm_1')
    graph = connectWorkflowNodes(graph, 'llm_1', 'end')

    expect(validateWorkflowGraph(graph).errors).toContain('大模型节点 llm_1 需要选择模型')
  })

  it('rejects missing fixed nodes', () => {
    const graph = deleteWorkflowNode(createDefaultWorkflowGraph(), 'llm_1')
    const withoutEnd = { ...graph, nodes: graph.nodes.filter((node) => node.nodeKey !== 'end') }

    expect(validateWorkflowGraph(withoutEnd).errors).toContain('END node is required')
  })
})
