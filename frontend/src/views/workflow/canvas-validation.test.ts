import { describe, expect, it } from 'vitest'

import { addWorkflowNode, connectWorkflowNodes, createDefaultWorkflowGraph } from './flowGraph'
import { validateWorkflowGraph } from './workflowValidation'

describe('canvas DAG topology validation', () => {
  it('allows explicit default fan-out and implicit joins', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'MESSAGE', { x: 320, y: 120 })
    graph = addWorkflowNode(graph, 'MESSAGE', { x: 320, y: 320 })
    graph = addWorkflowNode(graph, 'VARIABLE_AGGREGATION', { x: 560, y: 220 })
    graph = {
      ...graph,
      nodes: graph.nodes.map((node) =>
        node.nodeKey === 'start'
          ? { ...node, config: { ...node.config, ports: [{ key: 'default', allowFanOut: true }] } }
          : node,
      ),
    }
    graph = connectWorkflowNodes(graph, 'start', 'message_1')
    graph = connectWorkflowNodes(graph, 'start', 'message_2')
    graph = connectWorkflowNodes(graph, 'message_1', 'variable_aggregation_1')
    graph = connectWorkflowNodes(graph, 'message_2', 'variable_aggregation_1')
    graph = connectWorkflowNodes(graph, 'variable_aggregation_1', 'end')

    expect(validateWorkflowGraph(graph).errors).not.toContain('节点 start default 出口需要开启 fan-out 后才能连接多个下游')
    expect(validateWorkflowGraph(graph).valid).toBe(true)
  })

  it('rejects ambiguous default fan-out without allowFanOut', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'MESSAGE', { x: 320, y: 120 })
    graph = addWorkflowNode(graph, 'MESSAGE', { x: 320, y: 320 })
    graph = connectWorkflowNodes(graph, 'start', 'message_1')
    graph = connectWorkflowNodes(graph, 'start', 'message_2')
    graph = connectWorkflowNodes(graph, 'message_1', 'end')
    graph = connectWorkflowNodes(graph, 'message_2', 'end')

    expect(validateWorkflowGraph(graph).errors).toContain('节点 start default 出口需要开启 fan-out 后才能连接多个下游')
  })

  it('allows a side-effect terminal leaf without a path to END', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'API_CALL', { x: 320, y: 240 })
    graph = {
      ...graph,
      nodes: graph.nodes.map((node) =>
        node.nodeKey === 'api_call_1'
          ? {
              ...node,
              config: {
                ...node.config,
                resourceId: 'api-resource:notify',
                authMode: 'none',
                timeoutMs: 30000,
                retryCount: 0,
                errorBehavior: 'fail',
                outputParameters: [{ name: 'status', type: 'string' }],
                sideEffectTerminal: true,
              },
            }
          : node,
      ),
    }
    graph = connectWorkflowNodes(graph, 'start', 'api_call_1')

    expect(validateWorkflowGraph(graph).valid).toBe(true)
  })

  it('rejects connected islands that are not reachable from START', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'MESSAGE', { x: 320, y: 160 })
    graph = addWorkflowNode(graph, 'MESSAGE', { x: 320, y: 360 })
    graph = connectWorkflowNodes(graph, 'start', 'message_1')
    graph = connectWorkflowNodes(graph, 'message_1', 'end')
    graph = connectWorkflowNodes(graph, 'message_2', 'end')

    expect(validateWorkflowGraph(graph).errors).toContain('Node message_2 is not reachable from START')
  })
})
