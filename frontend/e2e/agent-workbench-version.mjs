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
  const providers = await unwrap(
    await page.request.get(`${baseUrl}/api/v1/providers?page=1&pageSize=100`),
    'list providers',
  )
  for (const provider of providers.list ?? []) {
    if (!provider.enabled) continue
    if (String(provider.baseUrl || '').startsWith('mock://')) continue
    for (const model of provider.models ?? []) {
      if (model.enabled) return model.id
    }
  }
  throw new Error('No enabled model found for Agent version e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const modelConfigId = await findEnabledModel(page)
  const agent = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `Version Workbench Agent ${Date.now()}`,
        description: 'agent version e2e',
        systemPrompt: 'You are testing agent versions.',
        openingMessage: '版本预览开场白',
        suggestedQuestions: ['如何发布版本？'],
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
  await page.getByTestId('agent-workbench-shell').waitFor({ state: 'visible', timeout: 5000 })
  await page.getByRole('button', { name: '发布', exact: true }).click()
  const versionPanel = page.getByTestId('agent-version-panel')
  await versionPanel.waitFor({ state: 'visible', timeout: 5000 })

  await page.getByRole('button', { name: '创建版本' }).click()
  await versionPanel.getByText('v1', { exact: true }).waitFor({ state: 'visible', timeout: 5000 })
  await versionPanel.getByRole('button', { name: '发布版本' }).click()
  await versionPanel.getByText('已发布', { exact: true }).waitFor({ state: 'visible', timeout: 5000 })
  await page.keyboard.press('Escape')
  await page.getByTestId('preview-target-select').getByText('Released v1').waitFor({ state: 'visible', timeout: 5000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent workbench version e2e')
} finally {
  await browser.close()
}
