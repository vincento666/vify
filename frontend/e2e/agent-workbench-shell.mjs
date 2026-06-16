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
  throw new Error('No enabled model found for Agent workbench e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/agents/new`, { waitUntil: 'networkidle' })
  await page.getByTestId('agent-workbench-shell').waitFor({ state: 'visible', timeout: 5000 })
  assert(await page.getByTestId('agent-workbench-nav').count() === 0, 'Expected section navigation to be removed')
  assert(await page.getByTestId('agent-workbench-editor').isVisible(), 'Expected editor area')
  assert(await page.getByTestId('agent-workbench-preview').isVisible(), 'Expected preview area')
  assert((await page.getByTestId('agent-workbench-shell').innerText()).includes('新建 Agent'), 'Expected create title')

  const modelConfigId = await findEnabledModel(page)
  const agent = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `Workbench Shell Agent ${Date.now()}`,
        description: 'agent workbench shell e2e',
        systemPrompt: 'You are testing the workbench shell.',
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
  const editShell = page.getByTestId('agent-workbench-shell')
  await editShell.waitFor({ state: 'visible', timeout: 5000 })
  await page.getByRole('button', { name: '修改 Agent 名称' }).getByText(agent.name, { exact: true }).waitFor({ state: 'visible', timeout: 5000 })
  assert(await page.getByTestId('agent-workbench-editor').isVisible(), 'Expected edit editor area')
  assert(await page.getByTestId('agent-workbench-preview').isVisible(), 'Expected edit preview area')

  await page.goto(`${baseUrl}/agent`, { waitUntil: 'networkidle' })
  await page.getByText('Agent 管理').waitFor({ state: 'visible', timeout: 5000 })
  await page.getByRole('button', { name: '新增 Agent' }).click()
  await page.waitForURL(`${baseUrl}/agents/new`, { timeout: 5000 })
  await page.getByTestId('agent-workbench-shell').waitFor({ state: 'visible', timeout: 5000 })
  assert(await page.locator('.el-dialog').count() === 0, 'Create entry should not open legacy dialog')

  await page.goto(`${baseUrl}/agent`, { waitUntil: 'networkidle' })
  await page.getByText('Agent 管理').waitFor({ state: 'visible', timeout: 5000 })
  const editEntries = page.getByRole('button', { name: '编辑' })
  assert(await editEntries.count() > 0, 'Expected at least one Agent edit entry')
  await editEntries.first().click()
  await page.waitForURL(/\/agents\/\d+\/workbench$/, { timeout: 5000 })
  await page.getByTestId('agent-workbench-shell').waitFor({ state: 'visible', timeout: 5000 })
  assert(await page.locator('.el-dialog').count() === 0, 'Edit entry should not open legacy dialog')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent workbench shell e2e')
} finally {
  await browser.close()
}
