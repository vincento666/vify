import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  if (!response.ok()) {
    const text = await response.text()
    throw new Error(`${label} HTTP ${response.status()} ${text}`)
  }
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function findXiaomiModel(page) {
  for (let pageNo = 1; pageNo <= 50; pageNo += 1) {
    const providers = await unwrap(
      await page.request.get(`${baseUrl}/api/v1/providers?page=${pageNo}&pageSize=100&enabled=true`),
      'list providers',
    )
    for (const provider of providers.list ?? []) {
      if (!provider.enabled || !provider.authConfigured || String(provider.baseUrl || '').startsWith('mock://')) continue
      const model = (provider.models ?? []).find((item) => item.enabled && item.modelId === 'xiaomi/mimo-v2-flash')
      if (model) return { provider, model }
    }
    if ((providers.list ?? []).length === 0 || pageNo * 100 >= providers.total) break
  }
  throw new Error('No enabled xiaomi/mimo-v2-flash provider model found')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const { provider, model } = await findXiaomiModel(page)
  const stamp = Date.now()
  const chatflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `Chatflow LLM Model Selection ${stamp}`,
      description: 'LLM model selection config e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 160, y: 180 } } } },
        {
          nodeKey: 'llm_1',
          type: 'LLM',
          name: '大模型',
          config: {
            systemPrompt: '只回复 OK',
            outputVariable: 'output',
            ui: { position: { x: 520, y: 160 } },
          },
        },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'answer', output: '{{llm_1.output}}', ui: { position: { x: 860, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
        { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create chatflow')

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-llm').click()
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByTestId('llm-model-display').click({ force: true })
  const picker = panel.getByTestId('llm-model-selector')
  await picker.waitFor({ state: 'visible', timeout: 8000 })
  await picker.getByPlaceholder('搜索模型名称、供应商或能力').fill('mimo')
  await picker.getByRole('button', { name: '搜索模型', exact: true }).click()
  const optionText = model.displayName || model.name || model.modelId
  await picker.locator('button').filter({ hasText: optionText }).first().click()

  await Promise.all([
    page.waitForResponse((response) =>
      response.url().includes(`/api/v1/chatflows/${chatflow.id}`) && response.request().method() === 'PUT',
    ),
    page.getByRole('button', { name: '保存', exact: true }).click(),
  ])

  const saved = await unwrap(await page.request.get(`${baseUrl}/api/v1/chatflows/${chatflow.id}`), 'load saved chatflow')
  const llm = saved.nodes.find((node) => node.nodeKey === 'llm_1')
  assert(llm, `Expected saved LLM node: ${JSON.stringify(saved.nodes)}`)
  assert(llm.config.model === model.modelId, `Expected model ${model.modelId}, got ${JSON.stringify(llm.config)}`)
  assert(Number(llm.config.modelConfigId) === model.id, `Expected modelConfigId ${model.id}, got ${JSON.stringify(llm.config)}`)
  assert(Number(llm.config.providerId) === provider.id, `Expected providerId ${provider.id}, got ${JSON.stringify(llm.config)}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow llm model selection config e2e')
} finally {
  await browser.close()
}
