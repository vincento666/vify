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
  throw new Error('No enabled model found for Agent publish e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const modelConfigId = await findEnabledModel(page)
  const agent = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `Publish Workbench Agent ${Date.now()}`,
        systemPrompt: 'You are testing publish channels.',
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
  await page.getByRole('button', { name: '发布', exact: true }).click()
  const versionPanel = page.getByTestId('agent-version-panel')
  await versionPanel.getByRole('button', { name: '创建版本' }).click()
  await versionPanel.getByRole('button', { name: '发布版本' }).click()
  await versionPanel.getByText('已发布', { exact: true }).waitFor({ state: 'visible', timeout: 5000 })

  await page.getByTestId('agent-publish-panel').getByRole('button', { name: '发布到 API' }).click()
  await page.getByText('PUBLISHED').waitFor({ state: 'visible', timeout: 5000 })
  await page.getByText('/api/public/agents/').waitFor({ state: 'visible', timeout: 5000 })
  await page.getByRole('button', { name: '取消发布' }).click()
  await page.getByText('UNPUBLISHED').waitFor({ state: 'visible', timeout: 5000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent workbench publish e2e')
} finally {
  await browser.close()
}
