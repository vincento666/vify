import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function findEnabledModel(page) {
  const providers = await unwrap(await page.request.get(`${baseUrl}/api/v1/providers?page=1&pageSize=100`), 'list providers')
  for (const provider of providers.list ?? []) {
    if (!provider.enabled) continue
    if (String(provider.baseUrl || '').startsWith('mock://')) continue
    for (const model of provider.models ?? []) {
      if (model.enabled) return model.id
    }
  }
  throw new Error('No enabled model found for Agent capability e2e')
}

async function selectInCard(page, cardText, optionText) {
  const card = page.locator('.capability-card', { hasText: cardText })
  await card.locator('.el-select').first().click()
  const option = page.locator('.el-select-dropdown__item', { hasText: optionText })
  await option.first().waitFor({ state: 'visible', timeout: 10000 })
  await option.first().click()
}

async function selectMcpTool(page, optionText) {
  await page.getByTestId('agent-mcp-tool-select').click()
  const option = page.locator('.el-select-dropdown__item', { hasText: optionText })
  await option.first().waitFor({ state: 'visible', timeout: 10000 })
  await option.first().click()
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const suffix = Date.now()
  const modelConfigId = await findEnabledModel(page)
  const mcp = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/mcp-servers`, {
      data: { name: `Workbench MCP ${suffix}`, endpoint: `http://127.0.0.1:${10000 + (suffix % 1000)}/mcp`, description: 'capability e2e' },
    }),
    'create mcp',
  )
  const kb = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/knowledge-bases`, {
      data: { name: `Workbench KB ${suffix}`, description: 'capability e2e' },
    }),
    'create kb',
  )
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name: `Workbench Workflow ${suffix}`,
        description: 'capability e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'] } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{start.USER_INPUT}}' } },
        ],
        edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
      },
    }),
    'create workflow',
  )
  const agent = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `Capability Agent ${suffix}`,
        description: 'capability e2e',
        systemPrompt: 'Capability e2e agent.',
        modelConfigId,
        temperature: 0.2,
        maxTokens: 256,
        maxContextTurns: 4,
        toolIds: [],
      },
    }),
    'create agent',
  )

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench`, { waitUntil: 'networkidle' })
  await page.getByTestId('agent-capability-cards').waitFor({ state: 'visible', timeout: 5000 })
  await selectMcpTool(page, mcp.name)
  await selectInCard(page, '知识库', kb.name)
  await selectInCard(page, '工作流', workflow.name)

  const saveButton = page.getByRole('button', { name: '保存配置', exact: true })
  assert(!(await saveButton.isDisabled()), 'Expected save enabled after capability changes')
  const toolResponse = page.waitForResponse((response) =>
    response.url().includes(`/api/v1/agents/${agent.id}/tools`) && response.request().method() === 'PUT',
  )
  await saveButton.click()
  await toolResponse

  const detail = await unwrap(await page.request.get(`${baseUrl}/api/v1/agents/${agent.id}`), 'get agent detail')
  assert(detail.toolIds.includes(mcp.id), `Expected tool binding ${mcp.id}, got ${detail.toolIds}`)
  assert(detail.knowledgeBaseId === kb.id, `Expected kb ${kb.id}, got ${detail.knowledgeBaseId}`)
  assert(detail.workflowId === workflow.id, `Expected workflow ${workflow.id}, got ${detail.workflowId}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent workbench capabilities e2e')
} finally {
  await browser.close()
}
