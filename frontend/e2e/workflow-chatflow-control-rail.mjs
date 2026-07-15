import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || ''
const rem = 16

const flows = [
  { label: 'workflow', api: 'workflows', path: 'workflows' },
  { label: 'chatflow', api: 'chatflows', path: 'chatflows' },
]

const nodeDefinitions = [
  ['start', 'START', '开始', { outputVariables: ['USER_INPUT'] }],
  ['llm_1', 'LLM', '大模型', { prompt: 'reply {{start.USER_INPUT}}', streamOutput: false }],
  ['condition_1', 'CONDITION', '选择器', {
    outputVariable: 'route',
    conditionBranches: [{ key: 'matched', name: '匹配', logic: 'AND', conditions: [{ left: '{{start.USER_INPUT}}', operator: 'equals', right: 'match' }] }],
  }],
  ['knowledge_1', 'KNOWLEDGE', '知识检索', { resourceId: '', query: '{{start.USER_INPUT}}', retrievalMode: 'auto' }],
  ['api_1', 'API_CALL', 'API 调用', { resourceId: '', endpoint: 'https://example.test', method: 'GET', timeout: 30 }],
  ['tool_1', 'TOOL_CALL', '工具调用', { resourceId: '', errorBehavior: 'fail' }],
  ['workflow_1', 'EXECUTE_WORKFLOW', '工作流', { resourceId: '' }],
  ['agent_1', 'AGENT_CALL', '智能体', { resourceId: '', messageTemplate: '{{start.USER_INPUT}}', streamOutput: false }],
  ['human_transfer_1', 'TRANSFER_TO_HUMAN', '转人工', { message: 'handoff', priority: 'normal', slaMinutes: 30 }],
  ['code_1', 'CODE', '代码', { language: 'python', code: "result = {'output': 'ok'}", timeout: 10 }],
  ['text_1', 'TEXT_PROCESS', '文本处理', { operation: 'trim', template: '{{start.USER_INPUT}}' }],
  ['json_1', 'JSON_PARSE', 'JSON 解析', { source: '{"name":"seed"}', fieldMap: [{ name: 'name', path: '$.name', type: 'string' }] }],
  ['aggregation_1', 'VARIABLE_AGGREGATION', '变量聚合', {
    strategy: 'first_non_empty',
    groups: [{ name: 'Group1', type: 'string', variables: [{ valueMode: 'literal', value: 'seed' }] }],
  }],
  ['assign_1', 'VARIABLE_ASSIGN', '变量赋值', { targetScope: 'flow', targetVariable: 'topic', sourceValueMode: 'literal', source: 'seed' }],
  ['intent_1', 'INTENT_RECOGNITION', '意图识别', {
    inputSource: '{{start.USER_INPUT}}', classifierMode: 'fake', intents: [{ key: 'refund', name: '退款', description: '退款请求', examples: ['退款'], branch: 'refund' }],
  }],
  ['message_1', 'MESSAGE', '消息', { content: '{{start.USER_INPUT}}', streamOutput: false, streamTarget: 'message', fallbackMode: 'aggregate' }],
  ['question_1', 'QUESTION', '问题', { question: '继续吗？', answerType: 'text', resumeBehavior: 'wait', timeoutSeconds: 0 }],
  ['human_input_1', 'HUMAN_INPUT', '人工输入', { prompt: '请复核', approvalMode: 'input', assigneeRole: 'support', inputSchema: [{ name: 'approved', type: 'boolean', required: true, description: '通过' }] }],
  ['info_1', 'INFORMATION_COLLECTION', '信息收集', {
    inputSource: '{{start.USER_INPUT}}', collectionKey: 'profile', extractorMode: 'fake', maxRounds: 2,
    fields: [{ name: 'phone', type: 'string', required: true, description: '手机号', targetScope: 'conversation', targetVariable: 'phone' }],
  }],
  ['end', 'END', '结束', { output: '{{start.USER_INPUT}}', outputFormat: '文本' }],
]

const nonExecutableSelectedNodeTypes = new Set([
  'START',
  'END',
  'CONDITION',
  'VARIABLE_AGGREGATION',
  'QUESTION',
  'HUMAN_INPUT',
  'INFORMATION_COLLECTION',
  'TRANSFER_TO_HUMAN',
])

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  if (!response.ok()) throw new Error(`${label} HTTP ${response.status()} ${await response.text()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

function fixturePayload(label) {
  const stamp = Date.now()
  const nodes = nodeDefinitions.map(([nodeKey, type, name, config], index) => ({
    nodeKey,
    type,
    name,
    config: { ...config, ui: { position: { x: 80 + (index % 4) * 340, y: 80 + Math.floor(index / 4) * 170 } } },
  }))
  const edges = nodeDefinitions
    .filter(([nodeKey]) => nodeKey !== 'start')
    .map(([nodeKey]) => ({ sourceNodeKey: 'start', targetNodeKey: nodeKey, condition: null }))
  return {
    name: `Spec 225 control rail ${label} ${stamp}`,
    description: 'temporary cleanable all-node form geometry audit fixture',
    nodes,
    edges,
  }
}

async function closeConfigPanel(page) {
  const panel = page.getByTestId('node-config-panel')
  if (!(await panel.isVisible().catch(() => false))) return
  await panel.getByRole('button', { name: '关闭配置', exact: true }).click()
  await panel.waitFor({ state: 'hidden', timeout: 10000 })
}

async function openNodePanel(page, nodeKey) {
  await closeConfigPanel(page)
  const node = page.locator(`.vue-flow__node[data-id="${nodeKey}"]`)
  await node.waitFor({ state: 'visible', timeout: 10000 })
  await node.click({ force: true })
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  return panel
}

async function expandAllSections(panel) {
  for (let attempt = 0; attempt < 16; attempt += 1) {
    const collapsed = panel.locator('.config-section-toggle[aria-expanded="false"]')
    if ((await collapsed.count()) === 0) return
    await collapsed.first().click()
  }
  throw new Error('Config sections did not expand within bounded attempts')
}

async function selectorMetrics(locator) {
  return locator.evaluateAll((elements) => elements
    .map((element) => {
      const rect = element.getBoundingClientRect()
      const panel = element.closest('[data-testid="node-config-panel"]')?.getBoundingClientRect()
      return {
        label: element.getAttribute('aria-label') || element.closest('.config-field')?.querySelector('label')?.textContent?.trim() || 'unnamed select',
        width: rect.width,
        left: rect.left,
        right: rect.right,
        panelWidth: panel?.width || 0,
        panelLeft: panel?.left || 0,
        panelRight: panel?.right || 0,
      }
    })
    .filter((metric) => metric.width > 0),
  )
}

function assertInsidePanel(metric, label) {
  assert(metric.left >= metric.panelLeft - 1, `${label} escapes panel left edge: ${JSON.stringify(metric)}`)
  assert(metric.right <= metric.panelRight + 1, `${label} escapes panel right edge: ${JSON.stringify(metric)}`)
}

async function assertControlRail(panel, flowLabel, nodeKey) {
  const genericSelectors = await selectorMetrics(panel.locator('.config-field > .ant-select'))
  for (const metric of genericSelectors) {
    const expectedWidth = Math.min(17 * rem, metric.panelWidth - 2 * rem)
    assert(
      metric.width >= expectedWidth - 1,
      `${flowLabel}/${nodeKey} ${metric.label} must use the full control rail: ${JSON.stringify({ ...metric, expectedWidth })}`,
    )
    assertInsidePanel(metric, `${flowLabel}/${nodeKey} ${metric.label}`)
  }

  const outputSelectors = await selectorMetrics(panel.locator('.end-output-format-row .ant-select, .output-format-row .ant-select'))
  for (const metric of outputSelectors) {
    const expectedWidth = Math.min(17 * rem, metric.panelWidth - 7.25 * rem)
    assert(
      metric.width >= expectedWidth - 1,
      `${flowLabel}/${nodeKey} output format selector must fill its rail: ${JSON.stringify({ ...metric, expectedWidth })}`,
    )
    assertInsidePanel(metric, `${flowLabel}/${nodeKey} output format selector`)
  }

  const structuredSelectors = await selectorMetrics(panel.locator([
    '.start-variable-row .ant-select',
    '.input-parameter-row .ant-select',
    '.output-parameter-row .ant-select',
    '.schema-input-mapping-row .ant-select',
    '.json-field-mapping-row .ant-select',
    '.human-input-schema-row .ant-select',
    '.collection-field-row .ant-select',
  ].join(', ')))
  for (const metric of structuredSelectors) {
    assert(metric.width >= 4 * rem, `${flowLabel}/${nodeKey} structured selector is too narrow: ${JSON.stringify(metric)}`)
    assert(metric.width <= 9 * rem, `${flowLabel}/${nodeKey} structured selector is too wide: ${JSON.stringify(metric)}`)
    assertInsidePanel(metric, `${flowLabel}/${nodeKey} structured selector`)
  }
}

async function auditControlRail(page, flow) {
  await page.goto(`${baseUrl}/${flow.path}/${flow.id}/canvas`, { waitUntil: 'networkidle' })
  for (const [nodeKey, nodeType] of nodeDefinitions) {
    const panel = await openNodePanel(page, nodeKey)
    const singleNodeActionCount = await panel.getByRole('button', { name: '试运行当前节点', exact: true }).count()
    const expectedSingleNodeActionCount = nonExecutableSelectedNodeTypes.has(nodeType) ? 0 : 1
    assert(
      singleNodeActionCount === expectedSingleNodeActionCount,
      `${flow.label}/${nodeKey} selected-node test availability must match the declared node contract`,
    )
    await expandAllSections(panel)
    await assertControlRail(panel, flow.label, nodeKey)
    if (screenshotDir && (nodeKey === 'workflow_1' || nodeKey === 'agent_1' || nodeKey === 'info_1' || nodeKey === 'end')) {
      await page.screenshot({ path: `${screenshotDir}/${flow.label}-${nodeKey}.png`, fullPage: true })
    }
  }

  const saveResponse = page.waitForResponse((candidate) =>
    candidate.url().includes(`/api/v1/${flow.api}/${flow.id}`) && candidate.request().method() === 'PUT',
  )
  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await unwrap(await saveResponse, `save ${flow.label}`)
  const persisted = await unwrap(await page.request.get(`${baseUrl}/api/v1/${flow.api}/${flow.id}`), `reload ${flow.label}`)
  assert(persisted.nodes.length === nodeDefinitions.length, `${flow.label} save/reload must retain every audited node`)
  for (const [nodeKey, type] of nodeDefinitions) {
    const node = persisted.nodes.find((item) => item.nodeKey === nodeKey)
    assert(node?.type === type, `${flow.label} save/reload must retain ${nodeKey}/${type}`)
    assert(node.config && Object.keys(node.config).length > 0, `${flow.label} save/reload must retain ${nodeKey} config`)
  }
}

async function cleanupFlows(page, created) {
  const failures = []
  for (const flow of created.reverse()) {
    try {
      await unwrap(await page.request.delete(`${baseUrl}/api/v1/${flow.api}/${flow.id}`), `cleanup ${flow.label}`)
    } catch (error) {
      failures.push(error instanceof Error ? error.message : String(error))
    }
  }
  assert(failures.length === 0, `Fixture cleanup failed: ${failures.join(' | ')}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1600, height: 960 } })
const created = []

try {
  for (const template of flows) {
    const flow = await unwrap(
      await page.request.post(`${baseUrl}/api/v1/${template.api}`, { data: fixturePayload(template.label) }),
      `create ${template.label}`,
    )
    const entry = { ...template, id: flow.id }
    created.push(entry)
    await auditControlRail(page, entry)
  }
  console.log('PASS workflow/chatflow all-node control rail e2e')
} finally {
  try {
    await cleanupFlows(page, created)
  } finally {
    await browser.close()
  }
}
