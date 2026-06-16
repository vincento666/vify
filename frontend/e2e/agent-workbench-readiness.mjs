import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR

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
  throw new Error('No enabled model found for Agent readiness e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const modelConfigId = await findEnabledModel(page)
  const agent = await unwrap(await page.request.post(`${baseUrl}/api/v1/agents`, {
    data: {
      name: `Readiness Agent ${Date.now()}`,
      description: 'readiness e2e',
      systemPrompt: 'Readiness e2e.',
      modelConfigId,
      temperature: 0.2,
      maxTokens: 256,
      maxContextTurns: 4,
      toolIds: [],
    },
  }), 'create readiness agent')

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '修改 Agent 名称' }).click()
  await page.getByPlaceholder('请输入 Agent 名称').fill(`${agent.name} Dirty`)
  await page.getByPlaceholder('请输入 Agent 名称').press('Enter')
  page.once('dialog', async (dialog) => {
    assert(dialog.message().includes('未保存更改'), `Unexpected dialog: ${dialog.message()}`)
    await dialog.dismiss()
  })
  await page.getByLabel('返回 Agent 列表').click()
  assert(page.url().includes(`/agents/${agent.id}/workbench`), 'Expected route guard to keep user on dirty workbench')

  page.once('dialog', async (dialog) => {
    await dialog.accept()
  })
  await page.getByLabel('返回 Agent 列表').click()
  await page.waitForURL(`${baseUrl}/agent`, { timeout: 10000 })
  await page.getByText('Agent 管理').waitFor({ state: 'visible', timeout: 5000 })

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench`, { waitUntil: 'networkidle' })
  if (screenshotDir) {
    await page.screenshot({ path: `${screenshotDir}/desktop-readiness.png`, fullPage: true })
    await page.setViewportSize({ width: 390, height: 844 })
    await page.screenshot({ path: `${screenshotDir}/mobile-readiness.png`, fullPage: true })
  }

  console.log('PASS agent workbench readiness e2e')
} finally {
  await browser.close()
}
