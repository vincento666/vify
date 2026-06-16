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
  throw new Error('No enabled model found for Agent flow link e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const modelConfigId = await findEnabledModel(page)
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `Agent Linked Chatflow ${Date.now()}`,
        description: 'agent flow link e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { x: 80, y: 120 } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { x: 520, y: 120 } },
        ],
        edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
      },
    }),
    'create chatflow',
  )
  const agent = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `Flow Link Agent ${Date.now()}`,
        systemPrompt: 'Use linked flow.',
        modelConfigId,
        temperature: 0.2,
        maxTokens: 512,
        maxContextTurns: 4,
        workflowId: chatflow.id,
        toolIds: [],
      },
    }),
    'create agent',
  )

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench`, { waitUntil: 'load' })
  await page.getByRole('button', { name: '打开画布' }).click()
  await page.waitForURL(`**/chatflows/${chatflow.id}/canvas`, { timeout: 10000 })
  await page.goBack({ waitUntil: 'load' })
  await page.getByTestId('agent-workbench-shell').waitFor({ state: 'visible', timeout: 10000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent workbench flow link e2e')
} finally {
  await browser.close()
}
