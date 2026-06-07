import { describe, expect, it } from 'vitest'

import { buildLocalVariableCatalog, buildVariableCatalog, formatVariableReference } from './variableCatalog'
import { addWorkflowNode, connectWorkflowNodes, createDefaultChatflowGraph, createDefaultWorkflowGraph } from './flowGraph'

describe('workflow variable catalog', () => {
  it('offers only START and connected upstream node outputs for a selected node', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'LLM', { x: 320, y: 240 })
    graph = addWorkflowNode(graph, 'CONDITION', { x: 620, y: 240 })
    graph = addWorkflowNode(graph, 'KNOWLEDGE', { x: 620, y: 520 })
    const llm = graph.nodes.find((node) => node.type === 'LLM')!
    const condition = graph.nodes.find((node) => node.type === 'CONDITION')!
    const knowledge = graph.nodes.find((node) => node.type === 'KNOWLEDGE')!

    llm.config.outputVariable = 'intent'
    knowledge.config.outputVariable = 'references'
    graph = connectWorkflowNodes(connectWorkflowNodes(graph, 'start', llm.nodeKey), llm.nodeKey, condition.nodeKey)

    const catalog = buildVariableCatalog(graph, condition.nodeKey)
    const references = catalog.flatMap((group) => group.items.map((item) => item.reference))

    expect(references).toEqual(expect.arrayContaining(['{{start.USER_INPUT}}', `{{${llm.nodeKey}.intent}}`]))
    expect(references).not.toContain(`{{${knowledge.nodeKey}.references}}`)
    expect(catalog.map((group) => group.title)).toEqual(['开始', '大模型'])
    expect(catalog.map((group) => group.sourceNodeKey)).toEqual(['start', llm.nodeKey])
  })

  it('formats inserted references with the workflow template syntax', () => {
    expect(formatVariableReference('llm_1', 'answer')).toBe('{{llm_1.answer}}')
  })

  it('uses declared output parameter rows as downstream variable options', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'LLM', { x: 320, y: 240 })
    const llm = graph.nodes.find((node) => node.type === 'LLM')!
    const end = graph.nodes.find((node) => node.type === 'END')!

    llm.config.outputVariable = 'legacy'
    llm.config.outputParameters = [
      { name: 'answer', type: 'string' },
      { name: 'reasoning', type: 'object' },
    ]
    graph = connectWorkflowNodes(connectWorkflowNodes(graph, 'start', llm.nodeKey), llm.nodeKey, end.nodeKey)

    const references = buildVariableCatalog(graph, end.nodeKey).flatMap((group) =>
      group.items.map((item) => item.reference),
    )

    expect(references).toEqual(expect.arrayContaining([`{{${llm.nodeKey}.answer}}`, `{{${llm.nodeKey}.reasoning}}`]))
    expect(references).not.toContain(`{{${llm.nodeKey}.legacy}}`)
  })

  it('keeps sibling branch-local variables out of the current branch picker', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'CONDITION', { x: 320, y: 240 })
    graph = addWorkflowNode(graph, 'LLM', { x: 620, y: 120 })
    graph = addWorkflowNode(graph, 'KNOWLEDGE', { x: 620, y: 420 })
    graph = addWorkflowNode(graph, 'MESSAGE', { x: 920, y: 120 })
    const condition = graph.nodes.find((node) => node.type === 'CONDITION')!
    const branchLlm = graph.nodes.find((node) => node.type === 'LLM')!
    const siblingKnowledge = graph.nodes.find((node) => node.type === 'KNOWLEDGE')!
    const message = graph.nodes.find((node) => node.type === 'MESSAGE')!

    branchLlm.config.outputVariable = 'branch_answer'
    siblingKnowledge.config.outputVariable = 'sibling_refs'
    graph = connectWorkflowNodes(connectWorkflowNodes(graph, 'start', condition.nodeKey), condition.nodeKey, branchLlm.nodeKey, 'vip')
    graph = connectWorkflowNodes(graph, condition.nodeKey, siblingKnowledge.nodeKey, 'kb')
    graph = connectWorkflowNodes(graph, branchLlm.nodeKey, message.nodeKey)

    const references = buildVariableCatalog(graph, message.nodeKey).flatMap((group) =>
      group.items.map((item) => item.reference),
    )

    expect(references).toContain(`{{${branchLlm.nodeKey}.branch_answer}}`)
    expect(references).not.toContain(`{{${siblingKnowledge.nodeKey}.sibling_refs}}`)
  })

  it('builds Coze-like source groups with typed variable rows', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'LLM', { x: 320, y: 240 })
    const llm = graph.nodes.find((node) => node.type === 'LLM')!
    const end = graph.nodes.find((node) => node.type === 'END')!

    llm.config.outputParameters = [
      { name: 'answer', type: 'string' },
      { name: 'reasoning', type: 'object' },
    ]
    graph = connectWorkflowNodes(connectWorkflowNodes(graph, 'start', llm.nodeKey), llm.nodeKey, end.nodeKey)

    const catalog = buildVariableCatalog(graph, end.nodeKey)

    expect(catalog.map((group) => [group.scope, group.title, group.sourceLabel])).toEqual([
      ['upstream', '开始', '开始'],
      ['upstream', '大模型', '大模型'],
    ])
    expect(catalog.flatMap((group) => group.items.map((item) => item.reference))).not.toEqual(
      expect.arrayContaining(['{{global.brand}}', '{{conversation.conversation_id}}', '{{sys.now}}']),
    )
    expect(catalog.find((group) => group.sourceNodeKey === llm.nodeKey)?.items).toEqual([
      expect.objectContaining({ variable: 'answer', type: 'string', reference: `{{${llm.nodeKey}.answer}}` }),
      expect.objectContaining({ variable: 'reasoning', type: 'object', reference: `{{${llm.nodeKey}.reasoning}}` }),
    ])
  })

  it('uses Coze Chatflow preset start variables without hardcoded global scopes', () => {
    const graph = createDefaultChatflowGraph()
    const end = graph.nodes.find((node) => node.nodeKey === 'end')!

    const catalog = buildVariableCatalog(graph, end.nodeKey, { flowType: 'CHATFLOW' })
    const references = catalog.flatMap((group) => group.items.map((item) => item.reference))

    expect(catalog.map((group) => group.title)).toEqual(['开始'])
    expect(catalog[0]?.items).toEqual([
      expect.objectContaining({ variable: 'USER_INPUT', label: 'USER_INPUT', type: 'string', reference: '{{start.USER_INPUT}}' }),
      expect.objectContaining({ variable: 'CONVERSATION_NAME', label: 'CONVERSATION_NAME', type: 'string', reference: '{{start.CONVERSATION_NAME}}' }),
    ])
    expect(references).not.toContain('{{user.tier}}')
    expect(references).not.toContain('{{global.brand}}')
    expect(references).not.toContain('{{sys.query}}')
    expect(references).not.toContain('{{sys.round}}')
    expect(references).not.toContain('{{start.sys.query}}')
    expect(references).not.toContain('{{start.sys.round}}')
    expect(references).not.toContain('{{conversation.conversation_id}}')
    expect(references).not.toContain('{{channel.source}}')
    expect(references).not.toContain('{{input.payload}}')
  })

  it('adds configured global memory variables without inventing system variables', () => {
    const graph = createDefaultChatflowGraph()
    const end = graph.nodes.find((node) => node.nodeKey === 'end')!

    const catalog = buildVariableCatalog(graph, end.nodeKey, {
      flowType: 'CHATFLOW',
      globalVariables: {
        user: [{ name: 'name', type: 'string' }],
        app: [{ name: 'brand', type: 'string' }],
        system: [{ name: 'sys_uuid', type: 'string' }],
      },
    })
    const references = catalog.flatMap((group) => group.items.map((item) => item.reference))

    expect(catalog.map((group) => group.title)).toEqual(['用户变量', '应用变量', '系统变量', '开始'])
    expect(references).toContain('{{user.name}}')
    expect(references).toContain('{{global.brand}}')
    expect(references).toContain('{{sys.sys_uuid}}')
    expect(references).toContain('{{start.USER_INPUT}}')
    expect(references).not.toContain('{{sys.round}}')
    expect(references).not.toContain('{{sys.query}}')
  })

  it('does not show unconfigured Chatflow scoped variables on workflow canvases', () => {
    const graph = createDefaultWorkflowGraph()
    const end = graph.nodes.find((node) => node.nodeKey === 'end')!

    const catalog = buildVariableCatalog(graph, end.nodeKey, { flowType: 'WORKFLOW' })
    const references = catalog.flatMap((group) => group.items.map((item) => item.reference))

    expect(catalog.map((group) => group.title)).toEqual([])
    expect(references).not.toContain('{{sys.query}}')
    expect(references).not.toContain('{{user.tier}}')
    expect(references).not.toContain('{{global.brand}}')
  })

  it('limits inline text references to current node declared input variables', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'LLM', { x: 320, y: 240 })
    graph = addWorkflowNode(graph, 'KNOWLEDGE', { x: 620, y: 240 })
    const llm = graph.nodes.find((node) => node.type === 'LLM')!
    const downstreamKnowledge = graph.nodes.find((node) => node.type === 'KNOWLEDGE')!

    llm.config.inputParameters = [
      { name: 'input', type: 'string', valueMode: 'reference', value: '{{start.USER_INPUT}}' },
      { name: 'locale', type: 'string', valueMode: 'reference', value: '{{global.locale}}' },
    ]
    llm.config.outputParameters = [{ name: 'answer', type: 'string' }]
    downstreamKnowledge.config.outputVariable = 'references'
    graph = connectWorkflowNodes(connectWorkflowNodes(graph, 'start', llm.nodeKey), llm.nodeKey, downstreamKnowledge.nodeKey)

    const catalog = buildLocalVariableCatalog(graph, llm.nodeKey)
    const references = catalog.flatMap((group) => group.items.map((item) => item.reference))

    expect(catalog.map((group) => group.title)).toEqual(['输入'])
    expect(references).toEqual(['{{input}}', '{{locale}}'])
    expect(references).not.toContain('{{start.USER_INPUT}}')
    expect(references).not.toContain('{{global.locale}}')
    expect(references).not.toContain(`{{${llm.nodeKey}.answer}}`)
    expect(references).not.toContain(`{{${downstreamKnowledge.nodeKey}.references}}`)
  })

  it('uses end node return rows as local inline variables without exposing upstream directly', () => {
    let graph = createDefaultWorkflowGraph()
    graph = addWorkflowNode(graph, 'LLM', { x: 320, y: 240 })
    const llm = graph.nodes.find((node) => node.type === 'LLM')!
    const end = graph.nodes.find((node) => node.type === 'END')!

    llm.config.outputParameters = [{ name: 'answer', type: 'string' }]
    end.config.outputParameters = [
      { name: 'final', type: 'string' },
      { name: 'debug', type: 'object' },
    ]
    graph = connectWorkflowNodes(connectWorkflowNodes(graph, 'start', llm.nodeKey), llm.nodeKey, end.nodeKey)

    const catalog = buildLocalVariableCatalog(graph, end.nodeKey)
    const references = catalog.flatMap((group) => group.items.map((item) => item.reference))

    expect(catalog.map((group) => group.title)).toEqual(['输出'])
    expect(references).toEqual(['{{final}}', '{{debug}}'])
    expect(references).not.toContain(`{{${llm.nodeKey}.answer}}`)
    expect(references).not.toContain('{{start.USER_INPUT}}')
  })
})
