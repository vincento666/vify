import { mkdir, writeFile } from 'node:fs/promises'

const defaultBaseUrl = 'http://127.0.0.1:5173'
const defaultOutputDir = '/Users/vincento/work/develop/hify/artifacts/goal-chatflow-workflow-node-uat'

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function request(baseUrl, path, options = {}, label = path) {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: options.headers || (options.body ? { 'content-type': 'application/json' } : undefined),
    ...options,
  })
  const text = await response.text()
  let payload = {}
  try {
    payload = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`${label} returned non-JSON HTTP ${response.status}: ${text}`)
  }
  assert(response.ok, `${label} HTTP ${response.status}: ${text}`)
  assert(payload.code === 200, `${label} API ${payload.message || text}`)
  return payload.data
}

const getJson = (baseUrl, path, label) => request(baseUrl, path, { method: 'GET' }, label)
const postJson = (baseUrl, path, data, label) => request(baseUrl, path, { method: 'POST', body: JSON.stringify(data) }, label)
const putJson = (baseUrl, path, data, label) => request(baseUrl, path, { method: 'PUT', body: JSON.stringify(data) }, label)

async function findOpenRouterQwenModel(baseUrl) {
  for (let page = 1; page <= 20; page += 1) {
    const providers = await getJson(baseUrl, `/api/v1/providers?page=${page}&pageSize=100`, 'list providers')
    for (const provider of providers.list ?? []) {
      if (!provider.enabled) continue
      if (String(provider.baseUrl || '') !== 'https://openrouter.ai/api/v1') continue
      for (const model of provider.models ?? []) {
        if (model.enabled && String(model.modelId || '') === 'qwen/qwen3.5-9b') {
          return model.id
        }
      }
    }
    if ((providers.list ?? []).length === 0 || page * 100 >= providers.total) break
  }
  throw new Error('OpenRouter qwen/qwen3.5-9b model config is required for node form UAT fixtures')
}

function node(nodeKey, type, name, config, x, y) {
  return { nodeKey, type, name, config: { ...config, ui: { position: { x, y } } } }
}

function edgeConditionKey(value) {
  const text = String(value ?? '').trim()
  return text.length > 0 ? text : null
}

function assertNodeEndpointsComplete(nodes, edges) {
  const outgoing = new Map()
  for (const edge of edges) {
    const keys = outgoing.get(edge.sourceNodeKey) || new Set()
    keys.add(edgeConditionKey(edge.condition))
    outgoing.set(edge.sourceNodeKey, keys)
  }
  for (const item of nodes) {
    if (item.type === 'END') continue
    const conditions = outgoing.get(item.nodeKey) || new Set()
    if (item.type === 'CONDITION') {
      for (const branch of item.config.conditionBranches || []) {
        assert(conditions.has(branch.key), `Fixture condition node ${item.nodeKey} missing downstream edge for ${branch.key}`)
      }
      assert(conditions.has(null), `Fixture condition node ${item.nodeKey} missing default downstream edge`)
      continue
    }
    if (item.type === 'INTENT_RECOGNITION') {
      const defaultIntent = edgeConditionKey(item.config.defaultIntent) || 'default'
      for (const intent of item.config.intents || []) {
        if (intent.key === defaultIntent) continue
        assert(conditions.has(intent.key), `Fixture intent node ${item.nodeKey} missing downstream edge for ${intent.key}`)
      }
      assert(conditions.has(null), `Fixture intent node ${item.nodeKey} missing fallback downstream edge`)
      continue
    }
    assert(conditions.has(null), `Fixture node ${item.nodeKey} missing default downstream edge`)
  }
}

async function createPublishedChildWorkflow(baseUrl, stamp) {
  const child = await postJson(baseUrl, '/api/v1/workflows', {
    name: `Form UAT Child ${stamp}`,
    description: 'form controls UAT child workflow',
    nodes: [
      node('start', 'START', '开始', { outputVariables: ['ticket'] }, 100, 160),
      node('message_1', 'MESSAGE', '消息', { content: 'child {{start.ticket}}', outputVariable: 'content' }, 420, 160),
      node('end', 'END', '结束', { outputVariable: 'summary', output: '{{message_1.content}}' }, 740, 160),
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'message_1', condition: null },
      { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
    ],
  }, 'create form child workflow')
  return putJson(baseUrl, `/api/v1/workflows/${child.id}`, {
    name: child.name,
    description: child.description,
    status: 'PUBLISHED',
    nodes: child.nodes,
    edges: child.edges,
  }, 'publish form child workflow')
}

async function createFixtures(baseUrl) {
  const stamp = Date.now()
  const modelConfigId = await findOpenRouterQwenModel(baseUrl)
  const kb = await postJson(baseUrl, '/api/v1/knowledge-bases', {
    name: `Form UAT KB ${stamp}`,
    description: 'form controls UAT knowledge base',
  }, 'create form knowledge base')
  const mcp = await postJson(baseUrl, '/api/v1/mcp-servers', {
    name: `Form UAT MCP ${stamp}`,
    endpoint: 'mock://tools',
    description: 'form controls UAT tool server',
  }, 'create form mcp server')
  const child = await createPublishedChildWorkflow(baseUrl, stamp)
  const agent = await postJson(baseUrl, '/api/v1/agents', {
    name: `Form UAT Agent ${stamp}`,
    description: 'form controls UAT agent',
    systemPrompt: 'Reply exactly with the user requested form UAT marker.',
    modelConfigId,
    temperature: 0,
    maxTokens: 80,
    maxContextTurns: 2,
    toolIds: [],
  }, 'create form agent')

  const nodes = [
    node('start', 'START', '开始', { outputVariables: ['USER_INPUT', 'CONVERSATION_NAME'] }, 60, 200),
    node('llm_1', 'LLM', '大模型', {
      modelConfigId,
      inputParameters: [{ name: 'seed_input', type: 'string', valueMode: 'literal', value: 'seed' }],
      outputParameters: [{ name: 'answer', type: 'string' }],
      prompt: 'seed {{start.USER_INPUT}}',
      outputVariable: 'answer',
    }, 340, 60),
    node('condition_1', 'CONDITION', '条件', {
      outputVariable: 'route',
      conditionBranches: [{ key: 'vip', name: 'VIP', logic: 'AND', conditions: [{ left: '{{start.USER_INPUT}}', operator: 'equals', right: 'vip' }] }],
      defaultBranch: 'normal',
    }, 340, 220),
    node('knowledge_1', 'KNOWLEDGE', '知识检索', {
      resourceId: `knowledge:${kb.id}`,
      knowledgeBaseId: kb.id,
      query: '{{start.USER_INPUT}}',
      topK: 2,
      outputVariable: 'answer',
      outputParameters: [{ name: 'answer', type: 'string' }],
    }, 340, 380),
    node('api_1', 'API_CALL', 'API 调用', {
      endpoint: 'http://127.0.0.1:65535/seed',
      method: 'GET',
      headers: '[]',
      body: '{}',
      timeout: 3,
      inputMappings: [{ name: 'query', type: 'string', required: true, valueMode: 'literal', value: 'seed' }],
      outputParameters: [{ name: 'response', type: 'string' }],
    }, 640, 60),
    node('tool_1', 'TOOL_CALL', '工具调用', {
      resourceType: 'MCP_TOOL',
      resourceId: `mcp:${mcp.id}:lookup_order`,
      serverIds: [mcp.id],
      toolName: 'lookup_order',
      inputMappings: [{ name: 'orderId', type: 'string', required: true, valueMode: 'literal', value: 'A-1' }],
      outputParameters: [{ name: 'result', type: 'string' }],
    }, 640, 220),
    node('workflow_1', 'EXECUTE_WORKFLOW', '工作流', {
      resourceId: `workflow:${child.id}`,
      targetWorkflowId: child.id,
      inputMappings: [{ name: 'ticket', type: 'string', required: true, valueMode: 'literal', value: 'T-1' }],
      outputParameters: [{ name: 'childSummary', type: 'string' }],
    }, 640, 380),
    node('agent_1', 'AGENT_CALL', '智能体', {
      resourceId: `agent:${agent.id}`,
      targetAgentId: agent.id,
      messageTemplate: '{{start.USER_INPUT}}',
      inputMappings: [{ name: 'message', type: 'string', required: true, valueMode: 'literal', value: 'hello' }],
      outputParameters: [{ name: 'agentAnswer', type: 'string' }],
    }, 940, 60),
    node('human_transfer_1', 'TRANSFER_TO_HUMAN', '转人工', {
      message: 'handoff seed',
      queue: 'general',
      reason: 'seed',
      priority: 'normal',
      slaMinutes: 30,
      outputParameters: [{ name: 'handoff_status', type: 'string' }],
    }, 940, 220),
    node('code_1', 'CODE', '代码', {
      language: 'python',
      code: "def main(args):\n    return {'output': args.get('input', '')}",
      timeout: 5,
      inputParameters: [{ name: 'input', type: 'string', valueMode: 'literal', value: 'seed' }],
      outputParameters: [{ name: 'output', type: 'string' }],
    }, 940, 380),
    node('text_1', 'TEXT_PROCESS', '文本处理', {
      operation: 'trim',
      template: 'seed {{start.USER_INPUT}}',
      source: '{{start.USER_INPUT}}',
      pattern: 'seed',
      replacement: 'audit',
      outputParameters: [{ name: 'text', type: 'string' }],
    }, 1240, 60),
    node('json_1', 'JSON_PARSE', 'JSON 解析', {
      source: '{"seed":"value"}',
      fieldMap: [{ name: 'seed', path: '$.seed', type: 'string' }],
      outputParameters: [{ name: 'seed', type: 'string' }],
    }, 1240, 220),
    node('aggregation_1', 'VARIABLE_AGGREGATION', '变量聚合', {
      groups: [{ name: 'SeedGroup', type: 'string', variables: [{ valueMode: 'literal', value: 'seed' }] }],
      outputParameters: [{ name: 'SeedGroup', type: 'string' }],
    }, 1240, 380),
    node('assign_1', 'VARIABLE_ASSIGN', '变量赋值', {
      targetScope: 'conversation',
      targetVariable: 'topic',
      sourceValueMode: 'literal',
      source: 'seed',
    }, 1540, 60),
    node('intent_1', 'INTENT_RECOGNITION', '意图识别', {
      inputSource: '{{start.USER_INPUT}}',
      classifierMode: 'fake',
      includeHistory: false,
      intents: [{ key: 'refund', name: '退款', description: 'seed', examples: ['退款'], branch: 'refund' }],
      outputParameters: [{ name: 'intent', type: 'string' }],
    }, 1540, 220),
    node('message_1', 'MESSAGE', '消息', {
      content: 'seed {{start.USER_INPUT}}',
      streamOutput: 'disabled',
      streamTarget: 'message',
      fallbackMode: 'aggregate',
      outputParameters: [{ name: 'content', type: 'string' }],
    }, 1540, 380),
    node('question_1', 'QUESTION', '问题', {
      question: 'seed?',
      answerType: 'text',
      resumeBehavior: 'wait',
      timeoutSeconds: 0,
      options: [{ label: 'Yes', value: 'yes' }],
      outputParameters: [{ name: 'answer', type: 'string' }],
    }, 1840, 60),
    node('human_input_1', 'HUMAN_INPUT', '人工输入', {
      prompt: 'review seed',
      approvalMode: 'input',
      assigneeRole: 'support',
      inputSchema: [{ name: 'approved', type: 'boolean', required: true, description: 'seed' }],
      outputParameters: [{ name: 'payload', type: 'object' }],
    }, 1840, 220),
    node('info_1', 'INFORMATION_COLLECTION', '信息收集', {
      inputSource: '{{start.USER_INPUT}}',
      collectionKey: 'profile',
      includeHistory: false,
      writeToConversation: false,
      extractorMode: 'fake',
      maxRounds: 2,
      streamOutput: 'disabled',
      fields: [{ name: 'phone', type: 'string', required: true, description: 'seed', targetScope: 'conversation', targetVariable: 'phone' }],
      outputParameters: [{ name: 'phone', type: 'string' }],
    }, 1840, 380),
    node('end', 'END', '结束', {
      outputVariable: 'final',
      output: 'seed {{start.USER_INPUT}}',
      streamOutput: 'disabled',
      outputParameters: [{ name: 'final', type: 'string', valueMode: 'literal', value: 'seed' }],
    }, 2140, 220),
  ]
  const edges = [
    { sourceNodeKey: 'start', targetNodeKey: 'condition_1', condition: null },
    { sourceNodeKey: 'condition_1', targetNodeKey: 'llm_1', condition: 'vip' },
    { sourceNodeKey: 'condition_1', targetNodeKey: 'knowledge_1', condition: null },
    { sourceNodeKey: 'llm_1', targetNodeKey: 'api_1', condition: null },
    { sourceNodeKey: 'api_1', targetNodeKey: 'tool_1', condition: null },
    { sourceNodeKey: 'tool_1', targetNodeKey: 'workflow_1', condition: null },
    { sourceNodeKey: 'workflow_1', targetNodeKey: 'agent_1', condition: null },
    { sourceNodeKey: 'agent_1', targetNodeKey: 'human_transfer_1', condition: null },
    { sourceNodeKey: 'human_transfer_1', targetNodeKey: 'code_1', condition: null },
    { sourceNodeKey: 'code_1', targetNodeKey: 'text_1', condition: null },
    { sourceNodeKey: 'text_1', targetNodeKey: 'json_1', condition: null },
    { sourceNodeKey: 'json_1', targetNodeKey: 'aggregation_1', condition: null },
    { sourceNodeKey: 'aggregation_1', targetNodeKey: 'assign_1', condition: null },
    { sourceNodeKey: 'assign_1', targetNodeKey: 'intent_1', condition: null },
    { sourceNodeKey: 'knowledge_1', targetNodeKey: 'intent_1', condition: null },
    { sourceNodeKey: 'intent_1', targetNodeKey: 'message_1', condition: 'refund' },
    { sourceNodeKey: 'intent_1', targetNodeKey: 'question_1', condition: null },
    { sourceNodeKey: 'message_1', targetNodeKey: 'human_input_1', condition: null },
    { sourceNodeKey: 'question_1', targetNodeKey: 'human_input_1', condition: null },
    { sourceNodeKey: 'human_input_1', targetNodeKey: 'info_1', condition: null },
    { sourceNodeKey: 'info_1', targetNodeKey: 'end', condition: null },
  ]
  assertNodeEndpointsComplete(nodes, edges)
  const chatflow = await postJson(baseUrl, '/api/v1/chatflows', {
    name: `Node Form Controls In-App UAT ${stamp}`,
    description: 'in-app browser UAT for every workflow/chatflow node form control',
    nodes,
    edges,
  }, 'create node form audit chatflow')
  return { stamp, chatflow, resources: { kb, mcp, child, agent, modelConfigId } }
}

async function ensureVisibleBrowser(browser) {
  await (await browser.capabilities.get('visibility')).set(true)
  let tab
  try {
    tab = await browser.tabs.selected()
  } catch {
    tab = undefined
  }
  if (!tab) tab = await browser.tabs.new()
  return tab
}

async function closeConfigPanelIfOpen(page) {
  const panel = page.getByTestId('node-config-panel')
  if ((await panel.count()) === 0 || !(await panel.isVisible().catch(() => false))) return
  const closeButton = panel.getByRole('button', { name: '关闭配置', exact: true })
  if ((await closeButton.count()) === 1) await closeButton.click({ force: true })
  await panel.waitFor({ state: 'hidden', timeoutMs: 5000 }).catch(() => undefined)
}

async function selectedPanelTitle(page) {
  const panel = page.getByTestId('node-config-panel')
  if ((await panel.count()) === 0) return ''
  return panel.locator('.config-header h3, .config-title-heading').innerText({ timeoutMs: 2000 }).catch(() => '')
}

async function selectCanvasNode(page, nodeKey, expectedTitle) {
  await closeConfigPanelIfOpen(page)
  const nodeLocator = page.locator(`.vue-flow__node[data-id="${nodeKey}"]`)
  await nodeLocator.waitFor({ state: 'attached', timeoutMs: 10000 })
  await nodeLocator.click({ force: true, timeoutMs: 5000 }).catch(async () => {
    await page.evaluate((key) => {
      const element = document.querySelector(`.vue-flow__node[data-id="${key}"]`)
      element?.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }))
    }, nodeKey)
  })
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeoutMs: 5000 })
  const title = (await selectedPanelTitle(page)).trim()
  assert(!expectedTitle || title === expectedTitle, `Expected ${nodeKey} panel ${expectedTitle}, got ${title}`)
  return panel
}

async function saveGraph(page) {
  const button = page.locator('button').filter({ hasText: '保存' })
  const count = await button.count()
  assert(count === 1, `Expected one save button, got ${count}`)
  await button.click({ force: true, timeoutMs: 5000 }).catch(async () => {
    const clicked = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'))
      const button = buttons.find((item) => (item.textContent || '').trim() === '保存')
      if (!button) return false
      const event = document.createEvent('MouseEvents')
      event.initEvent('click', true, true)
      button.dispatchEvent(event)
      return true
    }, undefined, { timeoutMs: 5000 })
    assert(clicked, 'Could not locate save button')
  })
  await page.waitForTimeout(700)
}

function getPath(obj, path) {
  return path.split('.').reduce((value, part) => {
    if (value === undefined || value === null) return undefined
    if (/^\d+$/.test(part)) return value[Number(part)]
    return value[part]
  }, obj)
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue)
  if (value && typeof value === 'object' && !(value instanceof RegExp)) {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableValue(value[key])]))
  }
  return value
}

function valueMatches(actual, expected) {
  if (expected instanceof RegExp) return expected.test(String(actual ?? ''))
  if (typeof expected === 'number') return Number(actual) === expected
  return JSON.stringify(stableValue(actual)) === JSON.stringify(stableValue(expected))
}

function record(results, node, control, interaction, configPath, actual, expected) {
  const passed = valueMatches(actual, expected)
  results.push({ node, control, interaction, configPath, expected: String(expected), actual, passed })
  assert(passed, `${node} ${control} expected ${String(expected)} at ${configPath}, got ${JSON.stringify(actual)}`)
}

function note(results, node, control, interaction, detail) {
  results.push({ node, control, interaction, configPath: 'N/A', expected: 'N/A', actual: detail, passed: true, status: 'not_rendered' })
}

async function latestNodeConfig(baseUrl, chatflowId, nodeKey) {
  const latest = await getJson(baseUrl, `/api/v1/chatflows/${chatflowId}`, `get chatflow ${chatflowId}`)
  const node = latest.nodes.find((item) => item.nodeKey === nodeKey)
  assert(node, `Missing node ${nodeKey} in saved chatflow`)
  return node.config || {}
}

async function latestChatflow(baseUrl, chatflowId) {
  return getJson(baseUrl, `/api/v1/chatflows/${chatflowId}`, `get chatflow ${chatflowId}`)
}

async function ensureBranchEdge(baseUrl, chatflowId, sourceNodeKey, condition, targetNodeKey) {
  const latest = await latestChatflow(baseUrl, chatflowId)
  const edgeExists = latest.edges.some(
    (edge) => edge.sourceNodeKey === sourceNodeKey && edge.condition === condition && edge.targetNodeKey === targetNodeKey,
  )
  if (edgeExists) return latest
  const updated = await putJson(baseUrl, `/api/v1/chatflows/${chatflowId}`, {
    name: latest.name,
    description: latest.description,
    status: latest.status,
    nodes: latest.nodes,
    edges: [...latest.edges, { sourceNodeKey, targetNodeKey, condition }],
  }, `connect ${sourceNodeKey}.${condition || 'default'} to ${targetNodeKey}`)
  return updated
}

async function assertSavedNodeEndpointsComplete(baseUrl, chatflowId) {
  const latest = await latestChatflow(baseUrl, chatflowId)
  assertNodeEndpointsComplete(latest.nodes, latest.edges)
  return latest
}

async function chooseOption(page, optionText) {
  const dropdown = page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)')
  const options = dropdown.locator('.ant-select-item-option').filter({ hasText: optionText })
  const count = await options.count()
  assert(count > 0, `Expected visible Ant option ${optionText}`)
  await options.nth(0).click({ force: true, timeoutMs: 5000 })
  await page.waitForTimeout(100)
}

function typeOptionLabel(type) {
  return {
    string: 'str.',
    number: 'num.',
    boolean: 'bool.',
    object: 'obj.',
    array: 'arr.',
  }[type] || type
}

async function fieldByLabel(scope, label) {
  const fields = scope.locator('.config-field').filter({ hasText: label })
  const count = await fields.count()
  assert(count > 0, `Expected config field ${label}`)
  return fields.nth(0)
}

async function fillField(scope, label, value) {
  const field = await fieldByLabel(scope, label)
  const inputs = field.locator('textarea, input:not([type="range"]):not([readonly])')
  const count = await inputs.count()
  assert(count > 0, `Expected editable input for ${label}`)
  await inputs.nth(count - 1).fill(String(value), { timeoutMs: 5000 })
}

async function selectField(page, scope, label, optionText) {
  const field = await fieldByLabel(scope, label)
  const selector = field.locator('.ant-select-selector')
  const count = await selector.count()
  assert(count > 0, `Expected select for ${label}`)
  await selector.nth(count - 1).click({ force: true, timeoutMs: 5000 })
  await chooseOption(page, optionText)
}

async function fillLabeledControl(scope, label, value) {
  const labels = scope.locator('label').filter({ hasText: label })
  const labelCount = await labels.count()
  assert(labelCount > 0, `Expected labeled control ${label}`)
  const inputs = labels.nth(0).locator('textarea, input:not([type="range"]):not([readonly])')
  const inputCount = await inputs.count()
  assert(inputCount > 0, `Expected editable labeled input ${label}`)
  await inputs.nth(inputCount - 1).fill(String(value), { timeoutMs: 5000 })
}

async function selectLabeledControl(page, scope, label, optionText) {
  const labels = scope.locator('label').filter({ hasText: label })
  const labelCount = await labels.count()
  assert(labelCount > 0, `Expected labeled select ${label}`)
  const selector = labels.nth(0).locator('.ant-select-selector')
  const selectorCount = await selector.count()
  assert(selectorCount > 0, `Expected labeled select trigger ${label}`)
  await selector.nth(selectorCount - 1).click({ force: true, timeoutMs: 5000 })
  await chooseOption(page, optionText)
}

async function toggleByLabel(scope, label) {
  const controls = scope.getByRole('switch', { name: label, exact: true })
  const count = await controls.count()
  assert(count > 0, `Expected switch ${label}`)
  await controls.nth(count - 1).click({ force: true, timeoutMs: 5000 })
}

async function addInputRow(panel, name, value) {
  const editor = panel.getByTestId('input-parameter-editor')
  const add = editor.getByRole('button', { name: '添加输入变量', exact: true })
  assert(await add.count() === 1, 'Expected add input variable button')
  await add.click({ force: true })
  const rows = editor.getByTestId('input-parameter-row')
  const row = rows.nth((await rows.count()) - 1)
  await row.getByPlaceholder('变量名').fill(name, { timeoutMs: 5000 })
  await row.getByLabel('输入变量值', { exact: true }).fill(value, { timeoutMs: 5000 })
}

async function addOutputRow(page, panel, name, type = 'number') {
  const editor = panel.getByTestId('output-parameter-editor')
  const add = editor.getByRole('button', { name: '添加输出变量', exact: true })
  assert(await add.count() === 1, 'Expected add output variable button')
  await add.click({ force: true })
  const rows = editor.getByTestId('output-parameter-row')
  const row = rows.nth((await rows.count()) - 1)
  await row.getByPlaceholder('变量名').fill(name, { timeoutMs: 5000 })
  await row.getByLabel('输出变量类型', { exact: true }).click({ force: true })
  await chooseOption(page, typeOptionLabel(type))
}

async function runCoreControls({ page, baseUrl, chatflowId, results }) {
  let panel = await selectCanvasNode(page, 'start', '开始')
  const startEditor = panel.getByTestId('start-variable-editor')
  await startEditor.getByRole('button', { name: '添加开始变量', exact: true }).click({ force: true })
  let rows = startEditor.getByTestId('start-variable-row')
  let row = rows.nth((await rows.count()) - 1)
  await row.getByPlaceholder('变量名').fill('audit_start', { timeoutMs: 5000 })
  await row.getByLabel('开始变量类型', { exact: true }).click({ force: true })
  await chooseOption(page, typeOptionLabel('number'))
  await row.getByLabel('开始变量必填', { exact: true }).setChecked(true, { force: true })
  await saveGraph(page)
  let config = await latestNodeConfig(baseUrl, chatflowId, 'start')
  const startVar = (config.startVariables || []).find((item) => item.name === 'audit_start')
  record(results, 'START', '开始变量名/类型/必填', 'add row + select + checkbox', 'startVariables.audit_start', startVar, { name: 'audit_start', type: 'number', required: true, builtIn: false })

  panel = await selectCanvasNode(page, 'llm_1', '大模型')
  await addInputRow(panel, 'audit_llm_input', 'literal-llm')
  await fillField(panel, '系统提示词', 'system {{start.USER_INPUT}} form audit')
  await fillField(panel, '用户提示词', 'prompt {{start.USER_INPUT}} {{audit_llm_input}} form audit')
  await toggleByLabel(panel.getByTestId('config-section-输出'), '流式输出')
  await addOutputRow(page, panel, 'audit_score', 'number')
  const toolSettings = panel.getByTestId('llm-tool-settings')
  await selectLabeledControl(page, toolSettings, '工具选择', 'required')
  await fillLabeledControl(toolSettings, '最大调用轮次', 2)
  await selectLabeledControl(page, toolSettings, '工具结果', 'separate')
  const modelSettings = panel.getByRole('button', { name: '模型设置', exact: true })
  assert(await modelSettings.count() === 1, 'Expected model settings button')
  await modelSettings.click({ force: true })
  const modelPanel = panel.getByTestId('llm-model-parameter-panel')
  await modelPanel.waitFor({ state: 'visible', timeoutMs: 5000 })
  const numberParams = { temperature: '0.23', maxTokens: '123', topP: '0.77', frequencyPenalty: '0.11', presencePenalty: '0.12', seed: '42' }
  for (const [key, value] of Object.entries(numberParams)) {
    const inputs = modelPanel.locator(`[data-testid="model-parameter-${key}"] input`)
    const count = await inputs.count()
    assert(count >= 2, `Expected model parameter input ${key}`)
    await inputs.nth(1).fill(value, { timeoutMs: 5000 })
  }
  await selectLabeledControl(page, modelPanel, '响应格式', 'JSON')
  await fillLabeledControl(modelPanel, '停止词', 'STOP_AUDIT')
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'llm_1')
  record(results, 'LLM', '输入参数', 'add literal row', 'inputParameters.last', config.inputParameters.at(-1), { name: 'audit_llm_input', type: 'string', valueMode: 'literal', value: 'literal-llm' })
  record(results, 'LLM', '系统提示词', 'textarea fill', 'systemPrompt', config.systemPrompt, 'system {{start.USER_INPUT}} form audit')
  record(results, 'LLM', '用户提示词', 'textarea fill', 'prompt', config.prompt, 'prompt {{start.USER_INPUT}} {{audit_llm_input}} form audit')
  record(results, 'LLM', '流式输出', 'switch toggle', 'streamOutput', config.streamOutput, 'enabled')
  record(results, 'LLM', '输出参数', 'add output row', 'outputParameters.last', config.outputParameters.at(-1), { name: 'audit_score', type: 'number' })
  record(results, 'LLM', '工具选择', 'select required', 'toolChoiceMode', config.toolChoiceMode, 'required')
  record(results, 'LLM', '最大调用轮次', 'number fill', 'maxToolRounds', config.maxToolRounds, 2)
  record(results, 'LLM', '工具结果', 'select separate', 'toolResultMode', config.toolResultMode, 'separate')
  record(results, 'LLM', '响应格式', 'select JSON', 'responseFormat', config.responseFormat, 'JSON')
  record(results, 'LLM', '停止词', 'textarea fill', 'stopSequences', config.stopSequences, 'STOP_AUDIT')
  for (const [key, value] of Object.entries({ temperature: 0.23, maxTokens: 123, topP: 0.77, frequencyPenalty: 0.11, presencePenalty: 0.12, seed: 42 })) {
    record(results, 'LLM', key, 'model parameter number fill', key, config[key], value)
  }

  panel = await selectCanvasNode(page, 'condition_1', '条件')
  const branchTitle = panel.getByTestId('condition-branch-title')
  assert(await branchTitle.count() > 0, 'Expected condition branch title')
  await branchTitle.nth(0).click({ force: true })
  await panel.getByLabel('分支名称', { exact: true }).fill('High Value', { timeoutMs: 5000 })
  await panel.getByLabel('分支名称', { exact: true }).press('Enter', { timeoutMs: 5000 })
  const op = panel.getByLabel('条件操作符', { exact: true })
  assert(await op.count() > 0, 'Expected condition operator')
  await op.nth(0).click({ force: true })
  await chooseOption(page, '包含')
  await panel.getByLabel('条件右值', { exact: true }).fill('audit-vip', { timeoutMs: 5000 })
  await panel.getByTestId('condition-default-title').click({ force: true })
  await panel.getByLabel('否则分支名称', { exact: true }).fill('Fallback Audit', { timeoutMs: 5000 })
  await panel.getByLabel('否则分支名称', { exact: true }).press('Enter', { timeoutMs: 5000 })
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'condition_1')
  record(results, 'CONDITION', '分支名称', 'inline edit', 'conditionBranches.0.name', config.conditionBranches[0].name, 'High Value')
  record(results, 'CONDITION', '条件操作符', 'select contains', 'conditionBranches.0.conditions.0.operator', config.conditionBranches[0].conditions[0].operator, 'contains')
  record(results, 'CONDITION', '条件右值', 'input fill', 'conditionBranches.0.conditions.0.right', config.conditionBranches[0].conditions[0].right, { valueMode: 'literal', value: 'audit-vip' })
  record(results, 'CONDITION', '否则分支名称', 'inline edit', 'defaultBranchName', config.defaultBranchName, 'Fallback Audit')

  panel = await selectCanvasNode(page, 'end', '结束')
  const textMode = panel.getByTestId('end-return-mode').getByRole('button', { name: '返回文本', exact: true })
  assert(await textMode.count() === 1, 'Expected END text mode')
  await textMode.click({ force: true })
  await panel.getByLabel('回答内容', { exact: true }).fill('final {{start.USER_INPUT}} form audit', { timeoutMs: 5000 })
  const variableMode = panel.getByTestId('end-return-mode').getByRole('button', { name: '返回变量', exact: true })
  assert(await variableMode.count() === 1, 'Expected END variable mode')
  await variableMode.click({ force: true })
  await addOutputRow(page, panel, 'audit_final', 'string')
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'end')
  record(results, 'END', '回答内容', 'textarea fill', 'output', config.output, 'final {{start.USER_INPUT}} form audit')
  record(results, 'END', '返回变量/输出参数', 'mode click + row add', 'outputParameters.last.name', config.outputParameters.at(-1).name, 'audit_final')
}

async function runResourceControls({ page, baseUrl, chatflowId, results }) {
  let panel = await selectCanvasNode(page, 'knowledge_1', '知识检索')
  await fillField(panel.getByTestId('config-section-知识库'), '检索问题', 'knowledge {{start.USER_INPUT}} audit')
  await selectField(page, panel.getByTestId('config-section-知识库'), '检索方式', '关键词匹配')
  await fillField(panel.getByTestId('config-section-知识库'), '返回条数', 4)
  await fillField(panel.getByTestId('config-section-知识库'), '最低命中分', 0.35)
  await toggleByLabel(panel.getByTestId('config-section-知识库'), '结果重排')
  await saveGraph(page)
  let config = await latestNodeConfig(baseUrl, chatflowId, 'knowledge_1')
  record(results, 'KNOWLEDGE', '检索问题', 'textarea fill', 'query', config.query, 'knowledge {{start.USER_INPUT}} audit')
  record(results, 'KNOWLEDGE', '检索方式', 'select keyword', 'retrievalMode', config.retrievalMode, 'keyword')
  record(results, 'KNOWLEDGE', '返回条数', 'number fill', 'topK', config.topK, 4)
  record(results, 'KNOWLEDGE', '最低命中分', 'number fill', 'scoreThreshold', config.scoreThreshold, 0.35)
  record(results, 'KNOWLEDGE', '结果重排', 'switch toggle', 'rerank', config.rerank, 'enabled')

  panel = await selectCanvasNode(page, 'api_1', 'API 调用')
  await fillField(panel.getByTestId('config-section-请求'), '请求地址', 'http://127.0.0.1:65535/audit/{{start.USER_INPUT}}')
  await selectField(page, panel.getByTestId('config-section-请求'), '请求方法', 'POST')
  await fillField(panel.getByTestId('config-section-请求'), '请求头', '[{"name":"X-Audit","value":"{{start.USER_INPUT}}"}]')
  await fillField(panel.getByTestId('config-section-请求'), '请求体', '{"audit":"{{start.USER_INPUT}}"}')
  await fillField(panel.getByTestId('config-section-请求'), '超时秒数', 17)
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'api_1')
  record(results, 'API_CALL', '请求地址', 'text fill', 'endpoint', config.endpoint, 'http://127.0.0.1:65535/audit/{{start.USER_INPUT}}')
  record(results, 'API_CALL', '请求方法', 'select POST', 'method', config.method, 'POST')
  record(results, 'API_CALL', '请求头', 'textarea fill', 'headers', config.headers, [{ name: 'X-Audit', value: '{{start.USER_INPUT}}' }])
  record(results, 'API_CALL', '请求体', 'textarea fill', 'body', config.body, '{"audit":"{{start.USER_INPUT}}"}')
  record(results, 'API_CALL', '超时秒数', 'number fill', 'timeout', config.timeout, 17)

  panel = await selectCanvasNode(page, 'tool_1', '工具调用')
  await fillField(panel.getByTestId('config-section-错误处理'), '重试次数', 3)
  await selectField(page, panel.getByTestId('config-section-错误处理'), '错误行为', 'continue')
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'tool_1')
  record(results, 'TOOL_CALL', '工具资源', 'resource select fixture', 'resourceType', config.resourceType, 'MCP_TOOL')
  record(results, 'TOOL_CALL', '适配器徽标', 'readonly badge visible', 'resourceId', String(config.resourceId || ''), /^mcp:/)
  record(results, 'TOOL_CALL', '重试次数', 'number fill', 'retryCount', config.retryCount, 3)
  record(results, 'TOOL_CALL', '错误行为', 'select continue', 'errorBehavior', config.errorBehavior, 'continue')

  panel = await selectCanvasNode(page, 'workflow_1', '工作流')
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'workflow_1')
  record(results, 'EXECUTE_WORKFLOW', '工作流资源', 'resource select fixture', 'targetWorkflowId', String(config.targetWorkflowId), /^\d+$/)
  record(results, 'EXECUTE_WORKFLOW', '参数映射', 'schema row persisted', 'inputMappings.0.value', config.inputMappings[0].value, 'T-1')

  panel = await selectCanvasNode(page, 'agent_1', '智能体')
  await fillField(panel.getByTestId('config-section-输入与上下文'), '消息模板', 'agent {{start.USER_INPUT}} audit')
  await selectField(page, panel.getByTestId('config-section-输入与上下文'), '会话历史', 'recent')
  await toggleByLabel(panel.getByTestId('config-section-输出'), '流式输出')
  await addOutputRow(page, panel, 'audit_agent_status', 'string')
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'agent_1')
  record(results, 'AGENT_CALL', '智能体资源', 'resource select fixture', 'targetAgentId', String(config.targetAgentId), /^\d+$/)
  record(results, 'AGENT_CALL', '消息模板', 'textarea fill', 'messageTemplate', config.messageTemplate, 'agent {{start.USER_INPUT}} audit')
  record(results, 'AGENT_CALL', '会话历史', 'select recent', 'historyMode', config.historyMode, 'recent')
  record(results, 'AGENT_CALL', '流式输出', 'switch toggle', 'streamOutput', config.streamOutput, 'enabled')
  record(results, 'AGENT_CALL', '输出参数', 'add row', 'outputParameters.last.name', config.outputParameters.at(-1).name, 'audit_agent_status')
}

async function runConversationControls({ page, baseUrl, chatflowId, results }) {
  let panel = await selectCanvasNode(page, 'human_transfer_1', '转人工')
  await fillField(panel.getByTestId('config-section-转接配置'), '转接提示', 'audit handoff {{start.USER_INPUT}}')
  await fillField(panel.getByTestId('config-section-转接配置'), '队列', 'vip-audit')
  await fillField(panel.getByTestId('config-section-转接配置'), '转接原因', 'audit_reason')
  await selectField(page, panel.getByTestId('config-section-转接配置'), '优先级', 'urgent')
  await fillField(panel.getByTestId('config-section-转接配置'), 'SLA 分钟', 45)
  await saveGraph(page)
  let config = await latestNodeConfig(baseUrl, chatflowId, 'human_transfer_1')
  record(results, 'TRANSFER_TO_HUMAN', '转接提示', 'textarea fill', 'message', config.message, 'audit handoff {{start.USER_INPUT}}')
  record(results, 'TRANSFER_TO_HUMAN', '队列', 'text fill', 'queue', config.queue, 'vip-audit')
  record(results, 'TRANSFER_TO_HUMAN', '转接原因', 'text fill', 'reason', config.reason, 'audit_reason')
  record(results, 'TRANSFER_TO_HUMAN', '优先级', 'select urgent', 'priority', config.priority, 'urgent')
  record(results, 'TRANSFER_TO_HUMAN', 'SLA 分钟', 'number fill', 'slaMinutes', config.slaMinutes, 45)

  panel = await selectCanvasNode(page, 'code_1', '代码')
  await selectField(page, panel.getByTestId('config-section-代码配置'), '语言', 'javascript')
  await panel.getByTestId('code-editor-field').locator('textarea').fill('exports.main = async (args) => ({ output: `audit ${args.input}` })', { timeoutMs: 5000 })
  await fillField(panel.getByTestId('config-section-代码配置'), '超时秒数', 9)
  await addInputRow(panel, 'audit_code_input', 'code literal')
  await addOutputRow(page, panel, 'audit_code_output', 'string')
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'code_1')
  record(results, 'CODE', '语言', 'select javascript', 'language', config.language, 'javascript')
  record(results, 'CODE', '代码', 'code editor fill', 'code', config.code, 'exports.main = async (args) => ({ output: `audit ${args.input}` })')
  record(results, 'CODE', '超时秒数', 'number fill', 'timeout', config.timeout, 9)
  record(results, 'CODE', '输入参数', 'add row', 'inputParameters.last.name', config.inputParameters.at(-1).name, 'audit_code_input')
  record(results, 'CODE', '输出参数', 'add row', 'outputParameters.last.name', config.outputParameters.at(-1).name, 'audit_code_output')

  panel = await selectCanvasNode(page, 'text_1', '文本处理')
  await selectField(page, panel.getByTestId('config-section-处理规则'), '操作', 'replace')
  await fillField(panel.getByTestId('config-section-处理规则'), '模板', 'audit template {{start.USER_INPUT}}')
  await fillField(panel.getByTestId('config-section-处理规则'), '源文本', 'seed source')
  await fillField(panel.getByTestId('config-section-处理规则'), '匹配表达式', 'seed')
  await fillField(panel.getByTestId('config-section-处理规则'), '替换为', 'audit')
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'text_1')
  record(results, 'TEXT_PROCESS', '操作', 'select replace', 'operation', config.operation, 'replace')
  record(results, 'TEXT_PROCESS', '模板', 'textarea fill', 'template', config.template, 'audit template {{start.USER_INPUT}}')
  record(results, 'TEXT_PROCESS', '源文本', 'textarea fill', 'source', config.source, 'seed source')
  record(results, 'TEXT_PROCESS', '匹配表达式', 'text fill', 'pattern', config.pattern, 'seed')
  record(results, 'TEXT_PROCESS', '替换为', 'text fill', 'replacement', config.replacement, 'audit')

  panel = await selectCanvasNode(page, 'json_1', 'JSON 解析')
  await fillField(panel.getByTestId('config-section-解析配置'), 'JSON 来源', '{"audit":{"id":7}}')
  const jsonEditor = panel.getByTestId('json-field-mapping-editor')
  await jsonEditor.getByRole('button', { name: '添加字段映射', exact: true }).click({ force: true })
  let rows = jsonEditor.getByTestId('json-field-mapping-row')
  let row = rows.nth((await rows.count()) - 1)
  await row.getByLabel('映射输出变量', { exact: true }).fill('audit_id', { timeoutMs: 5000 })
  await row.getByLabel('JSONPath', { exact: true }).fill('$.audit.id', { timeoutMs: 5000 })
  await row.getByLabel('字段变量类型', { exact: true }).click({ force: true })
  await chooseOption(page, typeOptionLabel('number'))
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'json_1')
  record(results, 'JSON_PARSE', 'JSON 来源', 'textarea fill', 'source', config.source, '{"audit":{"id":7}}')
  record(results, 'JSON_PARSE', '字段映射', 'add row', 'fieldMap.last', config.fieldMap.at(-1), { name: 'audit_id', path: '$.audit.id', type: 'number' })
}

async function runStructuredControls({ page, tab, baseUrl, chatflowId, results }) {
  let panel = await selectCanvasNode(page, 'aggregation_1', '变量聚合')
  const groupEditor = panel.getByTestId('aggregation-group-editor')
  await groupEditor.getByRole('button', { name: '新增分组', exact: true }).click({ force: true })
  const cards = groupEditor.getByTestId('aggregation-group-card')
  const card = cards.nth((await cards.count()) - 1)
  await card.getByTestId('aggregation-group-name-display').click({ force: true })
  await card.getByLabel('聚合分组名', { exact: true }).fill('AuditGroup', { timeoutMs: 5000 })
  await card.getByLabel('聚合分组名', { exact: true }).press('Enter', { timeoutMs: 5000 })
  const variableRows = card.getByTestId('aggregation-group-variable-row')
  await variableRows.nth(0).getByLabel('聚合变量值', { exact: true }).fill('literal aggregation', { timeoutMs: 5000 })
  await saveGraph(page)
  let config = await latestNodeConfig(baseUrl, chatflowId, 'aggregation_1')
  record(results, 'VARIABLE_AGGREGATION', '聚合策略', 'fixed official select', 'strategy', config.strategy, 'first_non_empty')
  record(results, 'VARIABLE_AGGREGATION', '变量分组名', 'add group + inline edit', 'groups.last.name', config.groups.at(-1).name, 'AuditGroup')
  record(results, 'VARIABLE_AGGREGATION', '聚合变量值', 'literal fill', 'groups.last.variables.0.value', config.groups.at(-1).variables[0].value, 'literal aggregation')
  record(results, 'VARIABLE_AGGREGATION', '输出摘要', 'derived output parameter', 'outputParameters.last.name', config.outputParameters.at(-1).name, 'AuditGroup')

  panel = await selectCanvasNode(page, 'assign_1', '变量赋值')
  const assignment = panel.getByTestId('variable-assignment-editor')
  await assignment.getByLabel('选择写入变量', { exact: true }).click({ force: true })
  const targetSources = assignment.getByTestId('assignment-target-source-item')
  const targetSourceCount = await targetSources.count()
  assert(targetSourceCount > 0, 'Expected writable variable target source')
  await targetSources.nth(0).click({ force: true })
  const targetOptions = assignment.getByTestId('assignment-target-option')
  const targetOptionCount = await targetOptions.count()
  assert(targetOptionCount > 0, 'Expected writable variable target option')
  await targetOptions.nth(0).click({ force: true })
  await assignment.getByLabel('赋值内容', { exact: true }).fill('audit assignment value', { timeoutMs: 5000 })
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'assign_1')
  record(results, 'VARIABLE_ASSIGN', '变量名称', 'target picker select', 'targetVariable', config.targetVariable, 'phone')
  record(results, 'VARIABLE_ASSIGN', '变量范围', 'target picker select', 'targetScope', config.targetScope, 'conversation')
  record(results, 'VARIABLE_ASSIGN', '赋值内容', 'literal fill', 'source', config.source, 'audit assignment value')
  record(results, 'VARIABLE_ASSIGN', '赋值模式', 'literal source mode', 'sourceValueMode', config.sourceValueMode, 'literal')

  panel = await selectCanvasNode(page, 'intent_1', '意图识别')
  await fillField(panel.getByTestId('config-section-识别策略'), '输入来源', '{{start.USER_INPUT}} audit intent')
  await selectField(page, panel.getByTestId('config-section-识别策略'), '分类模式', 'llm')
  await toggleByLabel(panel.getByTestId('config-section-识别策略'), '会话历史感知')
  const intentEditor = panel.getByTestId('intent-row-editor')
  await intentEditor.getByRole('button', { name: '添加意图', exact: true }).click({ force: true })
  const rows = intentEditor.getByTestId('intent-row')
  const row = rows.nth((await rows.count()) - 1)
  await row.getByLabel('意图名称', { exact: true }).fill('审计意图', { timeoutMs: 5000 })
  await row.getByLabel('意图描述', { exact: true }).fill('表单审计描述', { timeoutMs: 5000 })
  await row.getByLabel('意图示例', { exact: true }).fill('审计\naudit', { timeoutMs: 5000 })
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'intent_1')
  const newIntent = config.intents.at(-1)
  assert(newIntent?.key, 'Expected newly added intent key')
  const graphAfterIntentEdge = await ensureBranchEdge(baseUrl, chatflowId, 'intent_1', newIntent.key, 'human_input_1')
  if (tab) {
    await tab.reload()
    await page.waitForLoadState({ state: 'load', timeoutMs: 30000 }).catch(() => undefined)
    await page.getByText(graphAfterIntentEdge.name, { exact: false }).waitFor({ state: 'visible', timeoutMs: 30000 })
  }
  record(results, 'INTENT_RECOGNITION', '输入来源', 'textarea fill', 'inputSource', config.inputSource, '{{start.USER_INPUT}} audit intent')
  record(results, 'INTENT_RECOGNITION', '分类模式', 'select llm', 'classifierMode', config.classifierMode, 'llm')
  record(results, 'INTENT_RECOGNITION', '会话历史感知', 'switch toggle', 'includeHistory', config.includeHistory, 'true')
  record(results, 'INTENT_RECOGNITION', '意图行', 'add row', 'intents.last.name', newIntent.name, '审计意图')
  record(
    results,
    'INTENT_RECOGNITION',
    '新增意图分支下游',
    'add branch edge after adding intent',
    `edges.${newIntent.key}`,
    graphAfterIntentEdge.edges.find((edge) => edge.sourceNodeKey === 'intent_1' && edge.condition === newIntent.key)?.targetNodeKey,
    'human_input_1',
  )
}

async function runDialogControls({ page, baseUrl, chatflowId, results }) {
  let panel = await selectCanvasNode(page, 'message_1', '消息')
  await fillField(panel.getByTestId('config-section-发送消息'), '发送内容', 'message {{start.USER_INPUT}} audit')
  await toggleByLabel(panel.getByTestId('config-section-发送消息'), '流式输出')
  await selectField(page, panel.getByTestId('config-section-发送消息'), '流式目标', 'debug-only')
  await selectField(page, panel.getByTestId('config-section-发送消息'), '失败回退', 'fail')
  await saveGraph(page)
  let config = await latestNodeConfig(baseUrl, chatflowId, 'message_1')
  record(results, 'MESSAGE', '发送内容', 'textarea fill', 'content', config.content, 'message {{start.USER_INPUT}} audit')
  record(results, 'MESSAGE', '流式输出', 'switch toggle', 'streamOutput', config.streamOutput, 'enabled')
  record(results, 'MESSAGE', '流式目标', 'select debug-only', 'streamTarget', config.streamTarget, 'debug-only')
  record(results, 'MESSAGE', '失败回退', 'select fail', 'fallbackMode', config.fallbackMode, 'fail')

  panel = await selectCanvasNode(page, 'question_1', '问题')
  await fillField(panel.getByTestId('config-section-提问并等待'), '问题内容', 'question {{start.USER_INPUT}} audit?')
  await selectField(page, panel.getByTestId('config-section-提问并等待'), '答案类型', 'option')
  await selectField(page, panel.getByTestId('config-section-提问并等待'), '恢复行为', 'timeout_continue')
  await fillField(panel.getByTestId('config-section-提问并等待'), '超时秒数', 12)
  const optionEditor = panel.getByTestId('question-option-editor')
  await optionEditor.getByRole('button', { name: '添加回答选项', exact: true }).click({ force: true })
  let rows = optionEditor.getByTestId('question-option-row')
  let row = rows.nth((await rows.count()) - 1)
  await row.getByLabel('选项文案', { exact: true }).fill('审计选项', { timeoutMs: 5000 })
  await row.getByLabel('选项值', { exact: true }).fill('audit_option', { timeoutMs: 5000 })
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'question_1')
  record(results, 'QUESTION', '问题内容', 'textarea fill', 'question', config.question, 'question {{start.USER_INPUT}} audit?')
  record(results, 'QUESTION', '答案类型', 'select option', 'answerType', config.answerType, 'option')
  record(results, 'QUESTION', '恢复行为', 'select timeout_continue', 'resumeBehavior', config.resumeBehavior, 'timeout_continue')
  record(results, 'QUESTION', '超时秒数', 'number fill', 'timeoutSeconds', config.timeoutSeconds, 12)
  record(results, 'QUESTION', '回答选项', 'add option row', 'options.last', config.options.at(-1), { label: '审计选项', value: 'audit_option' })

  panel = await selectCanvasNode(page, 'human_input_1', '人工输入')
  await fillField(panel.getByTestId('config-section-人工处理'), '提示内容', 'human {{start.USER_INPUT}} audit')
  await selectField(page, panel.getByTestId('config-section-人工处理'), '审批模式', 'approval')
  await fillField(panel.getByTestId('config-section-人工处理'), '处理角色', 'audit-supervisor')
  const schemaEditor = panel.getByTestId('human-input-schema-editor')
  await schemaEditor.getByRole('button', { name: '添加人工输入字段', exact: true }).click({ force: true })
  rows = schemaEditor.getByTestId('human-input-schema-row')
  row = rows.nth((await rows.count()) - 1)
  await row.getByLabel('人工输入字段名', { exact: true }).fill('audit_decision', { timeoutMs: 5000 })
  await row.getByLabel('人工输入字段类型', { exact: true }).click({ force: true })
  await chooseOption(page, typeOptionLabel('string'))
  await row.getByLabel('人工输入字段必填', { exact: true }).setChecked(true, { force: true })
  await row.getByLabel('人工输入字段说明', { exact: true }).fill('审计说明', { timeoutMs: 5000 })
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'human_input_1')
  record(results, 'HUMAN_INPUT', '提示内容', 'textarea fill', 'prompt', config.prompt, 'human {{start.USER_INPUT}} audit')
  record(results, 'HUMAN_INPUT', '审批模式', 'select approval', 'approvalMode', config.approvalMode, 'approval')
  record(results, 'HUMAN_INPUT', '处理角色', 'text fill', 'assigneeRole', config.assigneeRole, 'audit-supervisor')
  record(results, 'HUMAN_INPUT', '输入结构', 'add schema row', 'inputSchema.last.name', config.inputSchema.at(-1).name, 'audit_decision')

  panel = await selectCanvasNode(page, 'info_1', '信息收集')
  await fillField(panel.getByTestId('config-section-收集策略'), '输入来源', '{{start.USER_INPUT}} audit collect')
  await fillField(panel.getByTestId('config-section-收集策略'), '状态键', 'audit_profile')
  await toggleByLabel(panel.getByTestId('config-section-收集策略'), '会话历史感知')
  await toggleByLabel(panel.getByTestId('config-section-收集策略'), '写入会话上下文')
  await selectField(page, panel.getByTestId('config-section-收集策略'), '抽取模式', 'llm')
  await fillField(panel.getByTestId('config-section-收集策略'), '最大收集轮次', 5)
  await toggleByLabel(panel.getByTestId('config-section-收集策略'), '追问流式输出')
  const fieldEditor = panel.getByTestId('collection-field-editor')
  await fieldEditor.getByRole('button', { name: '添加收集字段', exact: true }).click({ force: true })
  rows = fieldEditor.getByTestId('collection-field-row')
  row = rows.nth((await rows.count()) - 1)
  await row.getByLabel('收集字段名', { exact: true }).fill('audit_phone', { timeoutMs: 5000 })
  await row.getByLabel('收集字段类型', { exact: true }).click({ force: true })
  await chooseOption(page, typeOptionLabel('string'))
  await row.getByLabel('收集字段必填', { exact: true }).setChecked(true, { force: true })
  await row.getByLabel('收集字段说明', { exact: true }).fill('手机号审计', { timeoutMs: 5000 })
  await row.getByLabel('收集字段写入范围', { exact: true }).click({ force: true })
  await chooseOption(page, 'user')
  await row.getByLabel('收集字段目标变量', { exact: true }).fill('audit_phone_value', { timeoutMs: 5000 })
  await saveGraph(page)
  config = await latestNodeConfig(baseUrl, chatflowId, 'info_1')
  record(results, 'INFORMATION_COLLECTION', '输入来源', 'textarea fill', 'inputSource', config.inputSource, '{{start.USER_INPUT}} audit collect')
  record(results, 'INFORMATION_COLLECTION', '状态键', 'text fill', 'collectionKey', config.collectionKey, 'audit_profile')
  record(results, 'INFORMATION_COLLECTION', '会话历史感知', 'switch toggle', 'includeHistory', config.includeHistory, 'true')
  record(results, 'INFORMATION_COLLECTION', '写入会话上下文', 'switch toggle', 'writeToConversation', config.writeToConversation, 'true')
  record(results, 'INFORMATION_COLLECTION', '抽取模式', 'select llm', 'extractorMode', config.extractorMode, 'llm')
  record(results, 'INFORMATION_COLLECTION', '最大收集轮次', 'number fill', 'maxRounds', config.maxRounds, 5)
  record(results, 'INFORMATION_COLLECTION', '追问流式输出', 'switch toggle', 'streamOutput', config.streamOutput, 'enabled')
  record(results, 'INFORMATION_COLLECTION', '收集字段', 'add field row', 'fields.last.targetVariable', config.fields.at(-1).targetVariable, 'audit_phone_value')
}

async function writeReport(outputDir, stamp, summary) {
  const jsonPath = `${outputDir}/node-form-controls-audit-summary-${stamp}.json`
  const mdPath = `${outputDir}/node-form-controls-audit-summary-${stamp}.md`
  await writeFile(jsonPath, JSON.stringify(summary, null, 2))
  const byNode = new Map()
  for (const result of summary.results) {
    const rows = byNode.get(result.node) || []
    rows.push(result)
    byNode.set(result.node, rows)
  }
  const lines = [
    '# Workflow/Chatflow Node Form Controls In-App UAT',
    '',
    `- Chatflow: ${summary.chatflowId}`,
    `- Passed controls: ${summary.passed}/${summary.total}`,
    `- Screenshot: ${summary.screenshot}`,
    '',
  ]
  for (const [nodeName, rows] of byNode.entries()) {
    lines.push(`## ${nodeName}`)
    for (const row of rows) {
      lines.push(`- PASS ${row.control}: ${row.interaction}; saved ${row.configPath} = ${JSON.stringify(row.actual)}`)
    }
    lines.push('')
  }
  await writeFile(mdPath, `${lines.join('\n')}\n`)
  return { jsonPath, mdPath }
}

export async function runInAppNodeFormControlsAudit(options = {}) {
  const browser = options.browser || globalThis.browser
  assert(browser, 'in-app Browser is required')
  const baseUrl = options.baseUrl || defaultBaseUrl
  const outputDir = options.outputDir || defaultOutputDir
  await mkdir(outputDir, { recursive: true })
  await (await browser.capabilities.get('viewport')).set({ width: 1600, height: 900 })
  const tab = options.tab || await ensureVisibleBrowser(browser)
  globalThis.tab = tab
  const page = tab.playwright
  const fixtures = await createFixtures(baseUrl)
  await tab.goto(`${baseUrl}/chatflows/${fixtures.chatflow.id}/canvas`)
  await page.waitForLoadState({ state: 'load', timeoutMs: 30000 }).catch(() => undefined)
  await page.getByText(fixtures.chatflow.name, { exact: false }).waitFor({ state: 'visible', timeoutMs: 30000 })

  const results = []
  const context = { page, tab, baseUrl, chatflowId: fixtures.chatflow.id, results }
  const requestedGroups = new Set(options.groups || ['core', 'resource', 'conversation', 'structured', 'dialog'])
  if (requestedGroups.has('core')) await runCoreControls(context)
  if (requestedGroups.has('resource')) await runResourceControls(context)
  if (requestedGroups.has('conversation')) await runConversationControls(context)
  if (requestedGroups.has('structured')) await runStructuredControls(context)
  if (requestedGroups.has('dialog')) await runDialogControls(context)
  await assertSavedNodeEndpointsComplete(baseUrl, fixtures.chatflow.id)

  const screenshot = `${outputDir}/node-form-controls-audit-${fixtures.stamp}-${[...requestedGroups].join('-')}.png`
  await writeFile(screenshot, await tab.screenshot({ fullPage: true }))
  const summary = {
    stamp: fixtures.stamp,
    chatflowId: fixtures.chatflow.id,
    groups: [...requestedGroups],
    total: results.length,
    passed: results.filter((item) => item.passed).length,
    screenshot,
    results,
  }
  const report = await writeReport(outputDir, fixtures.stamp, summary)
  return { ...summary, ...report }
}
