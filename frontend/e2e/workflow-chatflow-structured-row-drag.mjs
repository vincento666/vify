import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || ''

const flows = [
  { label: 'workflow', api: 'workflows', path: 'workflows' },
  { label: 'chatflow', api: 'chatflows', path: 'chatflows' },
]

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  if (!response.ok()) {
    throw new Error(`${label} HTTP ${response.status()} ${await response.text()}`)
  }
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

function fixturePayload(label) {
  const stamp = Date.now()
  return {
    name: `Spec 225 structured drag ${label} ${stamp}`,
    description: 'temporary cleanable browser fixture for structured-row drag persistence',
    nodes: [
      {
        nodeKey: 'start',
        type: 'START',
        name: '开始',
        config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 120, y: 240 } } },
      },
      {
        nodeKey: 'condition_1',
        type: 'CONDITION',
        name: '多条件路由',
        config: {
          outputVariable: 'route',
          conditionBranches: [
            { key: 'priority', name: '优先', logic: 'AND', conditions: [{ left: '{{start.USER_INPUT}}', operator: 'contains', right: 'priority' }] },
            { key: 'standard', name: '标准', logic: 'AND', conditions: [{ left: '{{start.USER_INPUT}}', operator: 'contains', right: 'standard' }] },
            { key: 'fallback_rule', name: '兜底前', logic: 'AND', conditions: [{ left: '{{start.USER_INPUT}}', operator: 'contains', right: 'fallback' }] },
          ],
          ui: { position: { x: 480, y: 160 } },
        },
      },
      {
        nodeKey: 'aggregation_1',
        type: 'VARIABLE_AGGREGATION',
        name: '变量聚合',
        config: {
          strategy: 'first_non_empty',
          groups: [{
            name: 'ordered_values',
            type: 'string',
            variables: [
              { valueMode: 'literal', value: 'alpha' },
              { valueMode: 'literal', value: 'beta' },
              { valueMode: 'literal', value: 'gamma' },
            ],
          }],
          ui: { position: { x: 840, y: 240 } },
        },
      },
      {
        nodeKey: 'intent_1',
        type: 'INTENT_RECOGNITION',
        name: '意图识别',
        config: {
          inputSource: '{{start.USER_INPUT}}',
          classifierMode: 'fake',
          intents: [
            { key: 'refund', name: '退款', description: '退款请求', examples: ['我要退款'], branch: 'refund' },
            { key: 'invoice', name: '发票', description: '发票请求', examples: ['我要发票'], branch: 'invoice' },
            { key: 'other', name: '其他', description: '其他请求', examples: ['其他问题'], branch: 'other' },
          ],
          ui: { position: { x: 840, y: 460 } },
        },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: '结束',
        config: { output: '{{aggregation_1.ordered_values}}', ui: { position: { x: 1160, y: 240 } } },
      },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'condition_1', condition: null },
      { sourceNodeKey: 'condition_1', targetNodeKey: 'aggregation_1', condition: 'priority' },
      { sourceNodeKey: 'aggregation_1', targetNodeKey: 'end', condition: null },
    ],
  }
}

async function saveFlow(page, flow) {
  const response = page.waitForResponse((candidate) =>
    candidate.url().includes(`/api/v1/${flow.api}/${flow.id}`) && candidate.request().method() === 'PUT',
  )
  await page.getByRole('button', { name: '保存', exact: true }).click()
  await unwrap(await response, `save ${flow.label}`)
  await page.waitForTimeout(120)
  await page.reload({ waitUntil: 'networkidle' })
}

async function loadPersistedNode(page, flow, nodeKey) {
  const saved = await unwrap(
    await page.request.get(`${baseUrl}/api/v1/${flow.api}/${flow.id}`),
    `reload ${flow.label}`,
  )
  const node = saved.nodes.find((item) => item.nodeKey === nodeKey)
  assert(node, `Expected ${nodeKey} in persisted ${flow.label}: ${JSON.stringify(saved.nodes)}`)
  return node
}

async function openNodePanel(page, nodeKey, expectedConfigTestId) {
  const existingPanel = page.getByTestId('node-config-panel')
  if (await existingPanel.count()) {
    await existingPanel.getByRole('button', { name: '关闭配置', exact: true }).click()
    await existingPanel.waitFor({ state: 'hidden', timeout: 10000 })
  }
  const node = page.locator(`.vue-flow__node[data-id="${nodeKey}"]`)
  await node.waitFor({ state: 'visible', timeout: 10000 })
  await node.click({ force: true })
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByTestId(expectedConfigTestId).waitFor({ state: 'visible', timeout: 10000 })
  return panel
}

async function conditionNames(panel) {
  return (await panel.getByTestId('condition-branch-title').allTextContents()).map((value) => value.trim())
}

async function aggregationValues(group) {
  const rows = group.getByTestId('aggregation-group-variable-row')
  const values = []
  for (let index = 0; index < await rows.count(); index += 1) {
    const input = rows.nth(index).getByTestId('aggregation-variable-literal-input')
    values.push(await input.inputValue())
  }
  return values
}

async function intentNames(editor) {
  return editor.locator('input[aria-label="意图名称"]').evaluateAll((inputs) =>
    inputs.map((input) => input instanceof HTMLInputElement ? input.value : ''),
  )
}

async function assertDragAndPersistence(page, flow) {
  await page.goto(`${baseUrl}/${flow.path}/${flow.id}/canvas`, { waitUntil: 'networkidle' })

  let panel = await openNodePanel(page, 'condition_1', 'condition-branch-editor')
  const conditionEditor = panel.getByTestId('condition-branch-editor')
  const conditionCards = conditionEditor.getByTestId('condition-branch-card')
  const conditionHandles = conditionEditor.getByTestId('condition-drag-handle')
  assert(await conditionCards.count() === 3, `Expected three condition cards for ${flow.label}`)
  assert(await conditionHandles.count() === 3, `Condition rows need three real drag handles for ${flow.label}`)
  for (let index = 0; index < await conditionHandles.count(); index += 1) {
    assert(await conditionHandles.nth(index).getAttribute('draggable') === 'true', `Condition handle ${index} must be draggable for ${flow.label}`)
  }

  await conditionCards.nth(1).dispatchEvent('drop')
  assert(
    JSON.stringify(await conditionNames(panel)) === JSON.stringify(['优先', '标准', '兜底前']),
    `A condition drop without an active source must not reorder branches for ${flow.label}`,
  )

  await conditionHandles.nth(2).dragTo(conditionCards.nth(0))
  assert(
    JSON.stringify(await conditionNames(panel)) === JSON.stringify(['兜底前', '优先', '标准']),
    `Condition drag must reorder cards for ${flow.label}`,
  )
  await saveFlow(page, flow)
  panel = await openNodePanel(page, 'condition_1', 'condition-branch-editor')
  assert(
    JSON.stringify(await conditionNames(panel)) === JSON.stringify(['兜底前', '优先', '标准']),
    `Condition order must survive save/reload for ${flow.label}`,
  )
  const savedCondition = await loadPersistedNode(page, flow, 'condition_1')
  assert(
    JSON.stringify(savedCondition.config.conditionBranches.map((branch) => branch.key))
      === JSON.stringify(['fallback_rule', 'priority', 'standard']),
    `Condition persisted order must match UI for ${flow.label}`,
  )

  panel = await openNodePanel(page, 'intent_1', 'intent-row-editor')
  const intentEditor = panel.getByTestId('intent-row-editor')
  const intentRows = intentEditor.getByTestId('intent-row')
  const intentHandles = intentEditor.getByTestId('intent-drag-handle')
  assert(await intentRows.count() === 3, `Expected three intent rows for ${flow.label}`)
  assert(await intentHandles.count() === 3, `Expected three intent drag handles for ${flow.label}`)
  for (let index = 0; index < await intentHandles.count(); index += 1) {
    assert(await intentHandles.nth(index).getAttribute('draggable') === 'true', `Intent handle ${index} must be draggable for ${flow.label}`)
  }

  await intentRows.nth(1).dispatchEvent('drop')
  assert(
    JSON.stringify(await intentNames(intentEditor)) === JSON.stringify(['退款', '发票', '其他']),
    `An intent drop without an active source must not reorder rows for ${flow.label}`,
  )

  await intentHandles.nth(2).dragTo(intentRows.nth(0))
  assert(
    JSON.stringify(await intentNames(intentEditor)) === JSON.stringify(['其他', '退款', '发票']),
    `Intent drag must reorder rows for ${flow.label}`,
  )
  await saveFlow(page, flow)
  panel = await openNodePanel(page, 'intent_1', 'intent-row-editor')
  assert(
    JSON.stringify(await intentNames(panel.getByTestId('intent-row-editor'))) === JSON.stringify(['其他', '退款', '发票']),
    `Intent order must survive save/reload for ${flow.label}`,
  )
  const savedIntent = await loadPersistedNode(page, flow, 'intent_1')
  assert(
    JSON.stringify(savedIntent.config.intents.map((intent) => intent.key)) === JSON.stringify(['other', 'refund', 'invoice']),
    `Intent persisted order must match UI for ${flow.label}`,
  )

  panel = await openNodePanel(page, 'aggregation_1', 'aggregation-group-editor')
  const aggregationGroup = panel.getByTestId('aggregation-group-card').first()
  const aggregationRows = aggregationGroup.getByTestId('aggregation-group-variable-row')
  const aggregationHandles = aggregationGroup.getByTestId('aggregation-drag-handle')
  assert(await aggregationRows.count() === 4, `Expected three aggregation values plus one automatic candidate for ${flow.label}`)
  assert(await aggregationHandles.count() === 3, `Only persisted aggregation values should expose draggable handles for ${flow.label}`)
  for (let index = 0; index < await aggregationHandles.count(); index += 1) {
    assert(await aggregationHandles.nth(index).getAttribute('draggable') === 'true', `Aggregation handle ${index} must be draggable for ${flow.label}`)
  }

  await aggregationHandles.nth(2).dragTo(aggregationRows.nth(0))
  assert(
    JSON.stringify((await aggregationValues(aggregationGroup)).slice(0, 3)) === JSON.stringify(['gamma', 'alpha', 'beta']),
    `Aggregation drag must reorder rows for ${flow.label}`,
  )
  await saveFlow(page, flow)
  panel = await openNodePanel(page, 'aggregation_1', 'aggregation-group-editor')
  const reloadedAggregationGroup = panel.getByTestId('aggregation-group-card').first()
  assert(
    JSON.stringify((await aggregationValues(reloadedAggregationGroup)).slice(0, 3)) === JSON.stringify(['gamma', 'alpha', 'beta']),
    `Aggregation order must survive save/reload for ${flow.label}`,
  )
  const savedAggregation = await loadPersistedNode(page, flow, 'aggregation_1')
  assert(
    JSON.stringify(savedAggregation.config.groups[0].variables.map((variable) => variable.value).slice(0, 3))
      === JSON.stringify(['gamma', 'alpha', 'beta']),
    `Aggregation persisted order must match UI for ${flow.label}`,
  )

  if (screenshotDir) {
    await page.screenshot({ path: `${screenshotDir}/${flow.label}-structured-drag.png`, fullPage: true })
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
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const created = []

try {
  for (const flowTemplate of flows) {
    const createdFlow = await unwrap(
      await page.request.post(`${baseUrl}/api/v1/${flowTemplate.api}`, { data: fixturePayload(flowTemplate.label) }),
      `create ${flowTemplate.label}`,
    )
    const flow = { ...flowTemplate, id: createdFlow.id }
    created.push(flow)
    await assertDragAndPersistence(page, flow)
  }
  console.log('PASS workflow/chatflow structured row drag e2e')
} finally {
  try {
    await cleanupFlows(page, created)
  } finally {
    await browser.close()
  }
}
