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
  throw new Error('No enabled model found for Agent evaluation gate e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const modelConfigId = await findEnabledModel(page)
  const agent = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `Evaluation Gate Agent ${Date.now()}`,
        systemPrompt: 'release gate shell',
        modelConfigId,
        temperature: 0.2,
        maxTokens: 512,
        maxContextTurns: 4,
        toolIds: [],
        evaluationGate: { enabled: true, experimentId: 1, requiredPassRate: 0.8 },
      },
    }),
    'create agent',
  )
  const detail = await unwrap(await page.request.get(`${baseUrl}/api/v1/agents/${agent.id}`), 'agent detail')
  assert(detail.evaluationGate.enabled === true, 'evaluation gate should persist enabled')
  assert(detail.evaluationGate.requiredPassRate === 0.8, 'evaluation gate should persist required pass rate')

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench`, { waitUntil: 'load' })
  await page.getByRole('button', { name: '发布', exact: true }).click()
  const panel = page.getByTestId('agent-evaluation-gate-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.locator('summary').click()
  await panel.getByText('Evaluation Gate').waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByText('Required Pass Rate').waitFor({ state: 'visible', timeout: 5000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent workbench evaluation gate e2e')
} finally {
  await browser.close()
}
