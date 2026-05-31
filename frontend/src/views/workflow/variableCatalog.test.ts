import { describe, expect, it } from 'vitest'

import { buildVariableCatalog, formatVariableReference } from './variableCatalog'
import { addWorkflowNode, connectWorkflowNodes, createDefaultWorkflowGraph } from './flowGraph'

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
    expect(catalog.map((group) => group.title)).toEqual(['开始节点', '上游节点'])
  })

  it('formats inserted references with the workflow template syntax', () => {
    expect(formatVariableReference('llm_1', 'answer')).toBe('{{llm_1.answer}}')
  })
})
