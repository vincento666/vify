import type { WorkflowCanvasNode } from './flowGraph'
import { normalizeInputConfig } from './nodeConfig'

export type NodeTestInputRow = {
  name: string
  type: string
  value: string
}

type NodeTestFixtureOptions = {
  isChatflowMode?: boolean
  defaultMessage?: string
}

const DEFAULT_CHATFLOW_HISTORY = [
  { role: 'user', content: '上一轮用户问题' },
  { role: 'assistant', content: '上一轮助手回复' },
]

const CHATFLOW_RUNTIME_DEFAULTS: Array<{ name: string; type: string; value: string }> = [
  { name: 'sys.conversation_id', type: 'string', value: 'conv-node-test' },
  { name: 'sys.user_id', type: 'string', value: 'user-node-test' },
  { name: 'sys.channel', type: 'string', value: 'web' },
  { name: 'sys.round', type: 'number', value: '1' },
]

const NON_EXECUTABLE_SELECTED_NODE_TYPES = new Set([
  'START',
  'END',
  'CONDITION',
  'VARIABLE_AGGREGATION',
  'QUESTION',
  'HUMAN_INPUT',
  'INFORMATION_COLLECTION',
  'TRANSFER_TO_HUMAN',
])

export function buildNodeTestInputs(
  node: WorkflowCanvasNode,
  options: NodeTestFixtureOptions = {},
): NodeTestInputRow[] {
  const rows: NodeTestInputRow[] = []
  const rowIndex = new Map<string, number>()
  const defaultMessage = options.defaultMessage || 'hello'

  const add = (name: string, type = 'string', value = '', replaceEmpty = false) => {
    if (!name) return
    const index = rowIndex.get(name)
    if (index !== undefined) {
      if (replaceEmpty && !rows[index].value) {
        rows[index] = { ...rows[index], type, value }
      }
      return
    }
    rowIndex.set(name, rows.length)
    rows.push({ name, type, value })
  }

  for (const item of normalizeInputConfig(node.config).parameters) {
    add(item.name, item.type, String(item.value || ''))
  }
  if (node.type === 'START' && Array.isArray(node.config.outputVariables)) {
    for (const variable of node.config.outputVariables) {
      const name = String(variable || '').trim()
      add(name, inferredFixtureType(name), defaultFixtureValue(name, defaultMessage), true)
    }
  }
  for (const field of ['systemPrompt', 'prompt', 'expression', 'query', 'endpoint', 'headers', 'body', 'output']) {
    for (const reference of extractTemplateRefs(String(node.config[field] || ''))) {
      add(reference, inferredFixtureType(reference), defaultFixtureValue(reference, defaultMessage))
    }
  }
  for (const reference of extractTemplateRefs(JSON.stringify(node.config.conditionBranches || []))) {
    add(reference, inferredFixtureType(reference), defaultFixtureValue(reference, defaultMessage))
  }
  for (const reference of extractTemplateRefs(JSON.stringify(node.config.inputMappings || []))) {
    add(reference, inferredFixtureType(reference), defaultFixtureValue(reference, defaultMessage))
  }

  if (options.isChatflowMode) {
    add('sys.query', 'string', defaultMessage, true)
    for (const row of CHATFLOW_RUNTIME_DEFAULTS) {
      add(row.name, row.type, row.value, true)
    }
    if (node.type === 'LLM' && includeHistory(node.config)) {
      add('history', 'json', JSON.stringify(DEFAULT_CHATFLOW_HISTORY, null, 2), true)
    }
    return rows
  }

  if (node.type === 'LLM' && !rowIndex.has('userMessage')) {
    add('userMessage', 'string', defaultMessage)
  }
  return rows
}

export function canRunSingleNodeTest(node: Pick<WorkflowCanvasNode, 'type'> | null | undefined) {
  if (!node) return false
  return !NON_EXECUTABLE_SELECTED_NODE_TYPES.has(node.type)
}

export function nodeTestInputPayload(rows: NodeTestInputRow[]) {
  return rows.reduce<Record<string, any>>((payload, row) => {
    payload[row.name] = parseFixtureValue(row)
    if (row.name === 'userMessage') payload.USER_INPUT = payload[row.name]
    return payload
  }, {})
}

export function extractTemplateRefs(template: string) {
  const refs: string[] = []
  const pattern = /\{\{\s*([A-Za-z0-9_-]+)\.([A-Za-z0-9_.-]+)\s*\}\}/g
  for (const match of template.matchAll(pattern)) {
    refs.push(match[1] === 'start' ? match[2] : `${match[1]}.${match[2]}`)
  }
  return refs
}

function includeHistory(config: Record<string, any>) {
  return ['1', 'true', 'yes', 'on'].includes(String(config.includeHistory || '').toLowerCase())
}

function inferredFixtureType(reference: string) {
  if (reference === 'sys.round') return 'number'
  if (reference === 'history' || reference === 'conversationHistory') return 'json'
  return 'string'
}

function defaultFixtureValue(reference: string, defaultMessage: string) {
  if (reference === 'USER_INPUT') return defaultMessage
  if (reference === 'sys.query' || reference === 'userMessage') return defaultMessage
  if (reference === 'sys.conversation_id') return 'conv-node-test'
  if (reference === 'sys.user_id') return 'user-node-test'
  if (reference === 'sys.channel') return 'web'
  if (reference === 'sys.round') return '1'
  return ''
}

function parseFixtureValue(row: NodeTestInputRow) {
  if (!['json', 'object', 'array'].includes(row.type)) return row.value
  try {
    return JSON.parse(row.value)
  } catch {
    return row.value
  }
}
