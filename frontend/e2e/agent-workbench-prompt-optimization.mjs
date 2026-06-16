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
  throw new Error('No enabled model found for Agent prompt optimization e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const modelConfigId = await findEnabledModel(page)
  const agent = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `Prompt Optimize Agent ${Date.now()}`,
        systemPrompt: '你是客服。',
        modelConfigId,
        temperature: 0.2,
        maxTokens: 512,
        maxContextTurns: 4,
        toolIds: [],
      },
    }),
    'create agent',
  )

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench`, { waitUntil: 'load' })
  await page.getByRole('button', { name: 'Prompt 优化' }).click()
  const panel = page.getByTestId('agent-prompt-optimizer')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.locator('textarea[placeholder="输入优化要求"]').fill('让角色约束更清晰，并保持中文。')
  await panel.getByRole('button', { name: '生成优化草稿' }).click()
  await panel.getByRole('button', { name: '应用到 System Prompt' }).waitFor({ state: 'visible', timeout: 60000 })
  const originalPrompt = await page.locator('.prompt-editor textarea').inputValue()
  await panel.getByRole('button', { name: '应用到 System Prompt' }).click()
  const promptValue = await page.locator('.prompt-editor textarea').inputValue()
  assert(promptValue.trim().length > originalPrompt.trim().length, 'optimized prompt should be applied explicitly')
  assert(promptValue !== originalPrompt, 'optimized prompt should replace the original prompt')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent workbench prompt optimization e2e')
} finally {
  await browser.close()
}
