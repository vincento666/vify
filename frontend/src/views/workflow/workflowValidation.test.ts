import { describe, expect, it } from 'vitest'

import { addWorkflowNode, connectWorkflowNodes, createDefaultWorkflowGraph, deleteWorkflowNode } from './flowGraph'
import { mergeWorkflowValidationErrors, validateWorkflowGraph } from './workflowValidation'

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

  it('requires API call governance before run or publish', () => {
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
                resourceId: 'api:weather',
                endpoint: 'https://api.example.com/weather',
                method: 'POST',
                headers: '[{"name":"Authorization","value":"Bearer {{sys.api_token}}"}]',
              },
            }
          : node,
      ),
    }
    graph = connectWorkflowNodes(graph, 'start', 'api_call_1')
    graph = connectWorkflowNodes(graph, 'api_call_1', 'end')

    expect(validateWorkflowGraph(graph).errors).toEqual(
      expect.arrayContaining([
        'API 节点 api_call_1 需要配置认证策略',
        'API 节点 api_call_1 需要配置超时毫秒',
        'API 节点 api_call_1 需要配置重试次数',
        'API 节点 api_call_1 需要配置错误行为',
        'API 节点 api_call_1 需要配置输出 Schema',
        'API 节点 api_call_1 的敏感请求头 Authorization 需要加入脱敏列表',
      ]),
    )
  })

  it('requires tool call timeout, retry, error policy, and output schema governance', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'TOOL_CALL', { x: 320, y: 240 })
    graph = {
      ...graph,
      nodes: graph.nodes.map((node) =>
        node.nodeKey === 'tool_call_1'
          ? {
              ...node,
              config: {
                resourceId: 'mcp:server:lookup_order',
                resourceType: 'MCP_TOOL',
                toolName: 'lookup_order',
                inputMappings: [{ name: 'order_id', value: '{{start.USER_INPUT}}' }],
              },
            }
          : node,
      ),
    }
    graph = connectWorkflowNodes(graph, 'start', 'tool_call_1')
    graph = connectWorkflowNodes(graph, 'tool_call_1', 'end')

    expect(validateWorkflowGraph(graph).errors).toEqual(
      expect.arrayContaining([
        '工具节点 tool_call_1 需要配置超时毫秒',
        '工具节点 tool_call_1 需要配置重试次数',
        '工具节点 tool_call_1 需要配置错误行为',
        '工具节点 tool_call_1 需要配置输出 Schema',
      ]),
    )
  })

  it('requires regular node default output endpoints to connect downstream', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'MESSAGE', { x: 320, y: 240 })
    graph = connectWorkflowNodes(graph, 'start', 'end')
    graph = connectWorkflowNodes(graph, 'start', 'message_1')

    expect(validateWorkflowGraph(graph)).toEqual(
      expect.objectContaining({
        valid: false,
        errors: expect.arrayContaining(['节点 message_1 默认出口缺少下游连接']),
      }),
    )
  })

  it('requires every condition branch and fallback to have downstream edges', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'CONDITION', { x: 320, y: 240 })
    graph = {
      ...graph,
      nodes: graph.nodes.map((node) =>
        node.nodeKey === 'condition_1'
          ? {
              ...node,
              config: {
                ...node.config,
                conditionBranches: [{ key: 'vip', name: 'VIP' }],
                defaultBranch: 'normal',
              },
            }
          : node,
      ),
    }
    graph = connectWorkflowNodes(graph, 'start', 'condition_1')
    graph = connectWorkflowNodes(graph, 'condition_1', 'end', 'vip')

    expect(validateWorkflowGraph(graph)).toEqual(
      expect.objectContaining({
        valid: false,
        errors: expect.arrayContaining(['条件节点 condition_1 缺少默认分支下游连接']),
      }),
    )
  })

  it('requires every intent and fallback to have downstream edges', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'INTENT_RECOGNITION', { x: 320, y: 240 })
    graph = {
      ...graph,
      nodes: graph.nodes.map((node) =>
        node.nodeKey === 'intent_recognition_1'
          ? {
              ...node,
              config: {
                ...node.config,
                intents: [{ key: 'refund', name: '退款' }],
                defaultIntent: 'default',
              },
            }
          : node,
      ),
    }
    graph = connectWorkflowNodes(graph, 'start', 'intent_recognition_1')
    graph = connectWorkflowNodes(graph, 'intent_recognition_1', 'end', 'refund')

    expect(validateWorkflowGraph(graph)).toEqual(
      expect.objectContaining({
        valid: false,
        errors: expect.arrayContaining(['意图识别节点 intent_recognition_1 缺少兜底分支下游连接']),
      }),
    )
  })

  it('rejects missing fixed nodes', () => {
    const graph = deleteWorkflowNode(createDefaultWorkflowGraph(), 'llm_1')
    const withoutEnd = { ...graph, nodes: graph.nodes.filter((node) => node.nodeKey !== 'end') }

    expect(validateWorkflowGraph(withoutEnd).errors).toContain('END node is required')
  })

  it('deduplicates validation errors shared by run and publish checks', () => {
    expect(mergeWorkflowValidationErrors(['条件节点 condition_1 缺少默认分支下游连接'], [
      '条件节点 condition_1 缺少默认分支下游连接',
      '需要先完成一次成功试运行',
    ])).toEqual(['条件节点 condition_1 缺少默认分支下游连接', '需要先完成一次成功试运行'])
  })
})
