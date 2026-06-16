import { describe, expect, it } from 'vitest'

import { createDefaultChatflowGraph } from './flowGraph'
import { buildNodeTestInputs, canRunSingleNodeTest, nodeTestInputPayload } from './nodeTestFixtures'

describe('chatflow node test fixtures', () => {
  it('disables single-node test for fixed boundary nodes', () => {
    expect(canRunSingleNodeTest({ nodeKey: 'start', type: 'START' } as any)).toBe(false)
    expect(canRunSingleNodeTest({ nodeKey: 'end', type: 'END' } as any)).toBe(false)
    expect(canRunSingleNodeTest({ nodeKey: 'llm_1', type: 'LLM' } as any)).toBe(true)
  })

  it('only enables selected-node runs for executable nodes', () => {
    for (const type of ['CONDITION', 'VARIABLE_AGGREGATION', 'QUESTION', 'HUMAN_INPUT', 'INFORMATION_COLLECTION', 'TRANSFER_TO_HUMAN']) {
      expect(canRunSingleNodeTest({ nodeKey: type.toLowerCase(), type } as any)).toBe(false)
    }

    for (const type of ['LLM', 'KNOWLEDGE', 'API_CALL', 'TOOL_CALL', 'EXECUTE_WORKFLOW', 'AGENT_CALL', 'CODE', 'TEXT_PROCESS', 'JSON_PARSE', 'VARIABLE_ASSIGN', 'INTENT_RECOGNITION', 'MESSAGE']) {
      expect(canRunSingleNodeTest({ nodeKey: type.toLowerCase(), type } as any)).toBe(true)
    }
  })

  it('includes the Chatflow runtime profile variables for selected LLM node runs', () => {
    const graph = createDefaultChatflowGraph()
    const llm = {
      nodeKey: 'llm_1',
      type: 'LLM' as const,
      name: '大模型',
      position: { x: 300, y: 160 },
      config: {
        prompt: '用户问题：{{sys.query}}',
        includeHistory: 'true',
      },
    }

    const rows = buildNodeTestInputs(llm, { isChatflowMode: true, defaultMessage: '退款怎么处理' })

    expect(rows).toEqual(expect.arrayContaining([
      expect.objectContaining({ name: 'sys.query', type: 'string', value: '退款怎么处理' }),
      expect.objectContaining({ name: 'sys.conversation_id', type: 'string' }),
      expect.objectContaining({ name: 'sys.user_id', type: 'string' }),
      expect.objectContaining({ name: 'sys.channel', type: 'string' }),
      expect.objectContaining({ name: 'history', type: 'json' }),
    ]))

    const payload = nodeTestInputPayload(rows)
    expect(payload['sys.query']).toBe('退款怎么处理')
    expect(payload['sys.conversation_id']).toBeTruthy()
    expect(payload['sys.user_id']).toBeTruthy()
    expect(payload['sys.channel']).toBe('web')
    expect(payload.history).toEqual([
      { role: 'user', content: '上一轮用户问题' },
      { role: 'assistant', content: '上一轮助手回复' },
    ])
    expect(graph.nodes.find((node) => node.nodeKey === 'start')?.config.outputVariables).toEqual([
      'sys.query',
      'sys.conversation_id',
      'sys.user_id',
      'sys.channel',
      'sys.channel_id',
    ])
  })

  it('maps workflow userMessage to USER_INPUT without forcing Chatflow-only fields', () => {
    const llm = {
      nodeKey: 'llm_1',
      type: 'LLM' as const,
      name: '大模型',
      position: { x: 300, y: 160 },
      config: { prompt: 'Canvas prompt: {{start.userMessage}}' },
    }

    const rows = buildNodeTestInputs(llm, { isChatflowMode: false, defaultMessage: '单节点试运行' })
    const payload = nodeTestInputPayload(rows)

    expect(payload.userMessage).toBe('单节点试运行')
    expect(payload.USER_INPUT).toBe('单节点试运行')
    expect(payload['sys.query']).toBeUndefined()
    expect(payload.history).toBeUndefined()
  })

  it('uses START output variables as selected-node run inputs', () => {
    const start = {
      nodeKey: 'start',
      type: 'START' as const,
      name: '开始',
      position: { x: 120, y: 96 },
      config: { outputVariables: ['USER_INPUT', 'CONVERSATION_NAME'] },
    }

    const rows = buildNodeTestInputs(start, { isChatflowMode: false, defaultMessage: '矩阵输入' })

    expect(rows).toEqual(expect.arrayContaining([
      expect.objectContaining({ name: 'USER_INPUT', type: 'string', value: '矩阵输入' }),
      expect.objectContaining({ name: 'CONVERSATION_NAME', type: 'string', value: '' }),
    ]))
  })

  it('extracts selected-node inputs from condition branches', () => {
    const condition = {
      nodeKey: 'condition_1',
      type: 'CONDITION' as const,
      name: '条件',
      position: { x: 360, y: 120 },
      config: {
        conditionBranches: [
          {
            key: 'vip',
            logic: 'AND',
            conditions: [
              { left: '{{start.USER_INPUT}}', operator: 'equals', right: 'vip' },
              { left: '{{user.vip_level}}', operator: 'greater_or_equal', right: '3' },
            ],
          },
        ],
      },
    }

    const rows = buildNodeTestInputs(condition, { defaultMessage: 'vip' })

    expect(rows).toEqual(expect.arrayContaining([
      expect.objectContaining({ name: 'USER_INPUT', type: 'string', value: 'vip' }),
      expect.objectContaining({ name: 'user.vip_level', type: 'string', value: '' }),
    ]))
  })

  it('extracts selected-node inputs from API headers and body templates', () => {
    const api = {
      nodeKey: 'api_1',
      type: 'API_CALL' as const,
      name: 'API 调用',
      position: { x: 360, y: 120 },
      config: {
        endpoint: 'http://127.0.0.1:8765/orders/{{start.ORDER_ID}}',
        headers: '{"X-User":"{{user.id}}"}',
        body: '{"question":"{{llm.answer}}"}',
      },
    }

    const rows = buildNodeTestInputs(api, { defaultMessage: 'hello' })

    expect(rows).toEqual(expect.arrayContaining([
      expect.objectContaining({ name: 'ORDER_ID', type: 'string', value: '' }),
      expect.objectContaining({ name: 'user.id', type: 'string', value: '' }),
      expect.objectContaining({ name: 'llm.answer', type: 'string', value: '' }),
    ]))
  })

  it('extracts selected-node inputs from tool-call input mappings', () => {
    const toolCall = {
      nodeKey: 'tool_call_1',
      type: 'TOOL_CALL' as const,
      name: '工具调用',
      position: { x: 360, y: 120 },
      config: {
        inputMappings: [
          { name: 'orderId', valueMode: 'reference', value: '{{start.orderId}}', required: true },
          { name: 'reason', valueMode: 'reference', value: '{{conversation.reason}}' },
        ],
      },
    }

    const rows = buildNodeTestInputs(toolCall, { defaultMessage: 'A-100' })

    expect(rows).toEqual(expect.arrayContaining([
      expect.objectContaining({ name: 'orderId', type: 'string', value: '' }),
      expect.objectContaining({ name: 'conversation.reason', type: 'string', value: '' }),
    ]))
  })

  it('extracts selected-node inputs from execute-workflow input mappings', () => {
    const executeWorkflow = {
      nodeKey: 'execute_workflow_1',
      type: 'EXECUTE_WORKFLOW' as const,
      name: '工作流',
      position: { x: 360, y: 120 },
      config: {
        inputMappings: JSON.stringify([
          { name: 'ticket', valueMode: 'reference', value: '{{start.ticket}}', required: true },
          { name: 'priority', valueMode: 'reference', value: '{{global.priority}}' },
        ]),
      },
    }

    const rows = buildNodeTestInputs(executeWorkflow, { defaultMessage: 'A-100' })

    expect(rows).toEqual(expect.arrayContaining([
      expect.objectContaining({ name: 'ticket', type: 'string', value: '' }),
      expect.objectContaining({ name: 'global.priority', type: 'string', value: '' }),
    ]))
  })
})
