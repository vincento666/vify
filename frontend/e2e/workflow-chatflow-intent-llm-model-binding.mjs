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
  if (!response.ok()) throw new Error(`${label} HTTP ${response.status()} ${await response.text()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function findConfiguredQwen(page) {
  for (let pageNo = 1; pageNo <= 20; pageNo += 1) {
    const providers = await unwrap(
      await page.request.get(`${baseUrl}/api/v1/providers?page=${pageNo}&pageSize=100&enabled=true`),
      'list providers',
    )
    for (const provider of providers.list ?? []) {
      const model = (provider.models ?? []).find((item) =>
        provider.enabled && provider.authConfigured && item.enabled && item.modelId === 'qwen/qwen3.5-9b',
      )
      if (model) return { provider, model }
    }
    if ((providers.list ?? []).length === 0 || pageNo * 100 >= providers.total) break
  }
  throw new Error('Configured qwen/qwen3.5-9b model is required for this selector test')
}

function fixturePayload(label) {
  const stamp = Date.now()
  return {
    name: `Spec 225 Intent Model ${label} ${stamp}`,
    description: 'temporary cleanable intent model binding fixture',
    nodes: [
      { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 120, y: 160 } } } },
      {
        nodeKey: 'intent_1',
        type: 'INTENT_RECOGNITION',
        name: '意图识别',
        config: {
          inputSource: '{{start.USER_INPUT}}',
          outputVariable: 'intent',
          classifierMode: 'fake',
          defaultIntent: 'default',
          intents: [{ key: 'refund', name: '退款', description: '退款请求', examples: ['退款'] }],
          ui: { position: { x: 440, y: 160 } },
        },
      },
      { nodeKey: 'refund_end', type: 'END', name: '退款结束', config: { outputVariable: 'final', output: 'refund', ui: { position: { x: 780, y: 80 } } } },
      { nodeKey: 'default_end', type: 'END', name: '默认结束', config: { outputVariable: 'final', output: 'default', ui: { position: { x: 780, y: 280 } } } },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'intent_1', condition: null },
      { sourceNodeKey: 'intent_1', targetNodeKey: 'refund_end', condition: 'refund' },
      { sourceNodeKey: 'intent_1', targetNodeKey: 'default_end', condition: null },
    ],
  }
}

async function fieldByLabel(scope, label) {
  const fields = scope.locator('.config-field').filter({ hasText: label })
  assert(await fields.count() > 0, `Expected config field ${label}`)
  return fields.first()
}

async function chooseClassifierMode(page, panel) {
  const field = await fieldByLabel(panel.getByTestId('config-section-识别策略'), '分类模式')
  await field.scrollIntoViewIfNeeded()
  const selector = field.locator('.ant-select-selector')
  await selector.click({ force: true })
  await page.keyboard.press('ArrowDown')
  await page.keyboard.press('Enter')
  assert((await field.innerText()).includes('llm'), 'Expected classifier mode to switch to llm')
}

async function save(page, flow) {
  const response = page.waitForResponse((candidate) =>
    candidate.url().includes(`/api/v1/${flow.api}/${flow.id}`) && candidate.request().method() === 'PUT',
  )
  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await unwrap(await response, `save ${flow.label}`)
}

async function exerciseIntentModelBinding(page, flow, modelChoice) {
  await page.goto(`${baseUrl}/${flow.path}/${flow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="intent_1"]').click({ force: true })
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  await chooseClassifierMode(page, panel)

  const modelSection = panel.getByTestId('llm-model-section')
  await modelSection.waitFor({ state: 'visible', timeout: 5000 })
  await modelSection.getByTestId('llm-model-display').click({ force: true })
  const picker = panel.getByTestId('llm-model-selector')
  await picker.waitFor({ state: 'visible', timeout: 5000 })
  const optionText = modelChoice.model.displayName || modelChoice.model.name || modelChoice.model.modelId
  const option = picker.getByTestId('llm-model-option').filter({ hasText: optionText })
  assert(await option.count() > 0, `${flow.label} should offer ${optionText} for an LLM Intent`)
  await option.first().click({ force: true })
  await save(page, flow)

  const saved = await unwrap(await page.request.get(`${baseUrl}/api/v1/${flow.api}/${flow.id}`), `reload ${flow.label}`)
  const intent = saved.nodes.find((node) => node.nodeKey === 'intent_1')
  assert(intent?.config?.classifierMode === 'llm', `${flow.label} must persist LLM classifier mode`)
  assert(intent?.config?.model === modelChoice.model.modelId, `${flow.label} must persist selected model id`)
  assert(Number(intent?.config?.modelConfigId) === modelChoice.model.id, `${flow.label} must persist model config id`)
  assert(Number(intent?.config?.providerId) === modelChoice.provider.id, `${flow.label} must persist provider id`)

  await page.reload({ waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="intent_1"]').click({ force: true })
  await panel.getByTestId('llm-model-section').waitFor({ state: 'visible', timeout: 5000 })
  assert(
    (await panel.getByTestId('llm-model-display').innerText()).includes(optionText),
    `${flow.label} model display must survive reload`,
  )
  if (screenshotDir) await page.screenshot({ path: `${screenshotDir}/${flow.label}-intent-model-binding.png`, fullPage: true })
}

async function cleanup(page, created) {
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
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })
const created = []

try {
  const modelChoice = await findConfiguredQwen(page)
  for (const template of flows) {
    const createdFlow = await unwrap(
      await page.request.post(`${baseUrl}/api/v1/${template.api}`, { data: fixturePayload(template.label) }),
      `create ${template.label}`,
    )
    const flow = { ...template, id: createdFlow.id }
    created.push(flow)
    await exerciseIntentModelBinding(page, flow, modelChoice)
  }
  console.log('PASS workflow/chatflow Intent LLM model binding e2e')
} finally {
  try {
    await cleanup(page, created)
  } finally {
    await browser.close()
  }
}
