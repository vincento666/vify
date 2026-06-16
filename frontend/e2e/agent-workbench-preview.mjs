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
  for (let pageNo = 1; pageNo <= 20; pageNo += 1) {
    const providers = await unwrap(
      await page.request.get(`${baseUrl}/api/v1/providers?page=${pageNo}&pageSize=100`),
      'list providers',
    )
    for (const provider of providers.list ?? []) {
      if (!provider.enabled) continue
      if (String(provider.baseUrl || '').startsWith('mock://')) continue
      for (const model of provider.models ?? []) {
        if (model.enabled) return model.id
      }
    }
    if ((providers.list ?? []).length === 0 || pageNo * 100 >= providers.total) break
  }
  throw new Error('No enabled model found for Agent preview e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const modelConfigId = await findEnabledModel(page)

  await page.goto(`${baseUrl}/agents/new`, { waitUntil: 'networkidle' })
  assert((await page.getByTestId('agent-workbench-preview').innerText()).includes('请先保存 Agent 后再预览。'), 'Expected save-before-preview message')

  const agent = await unwrap(await page.request.post(`${baseUrl}/api/v1/agents`, {
    data: {
      name: `Preview Agent ${Date.now()}`,
      description: 'preview e2e',
      systemPrompt: 'For preview validation, answer with exactly AGENT_PREVIEW_OK when asked for the marker.',
      modelConfigId,
      temperature: 0,
      maxTokens: 64,
      maxContextTurns: 2,
      toolIds: [],
    },
  }), 'create preview agent')

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench`, { waitUntil: 'networkidle' })
  const preview = page.getByTestId('agent-workbench-preview')
  await preview.getByPlaceholder('输入预览消息').fill('Return the marker now: AGENT_PREVIEW_OK')
  await preview.getByRole('button', { name: '发送预览消息', exact: true }).click()
  await preview.getByText('AGENT_PREVIEW_OK').waitFor({ state: 'visible', timeout: 60000 })
  await preview.getByRole('button', { name: '打开调试详情' }).click()
  const debugPanel = page.getByTestId('agent-debug-detail-panel')
  await debugPanel.getByText('调试详情').waitFor({ state: 'visible', timeout: 5000 })
  await debugPanel.getByText('调用树').waitFor({ state: 'visible', timeout: 5000 })
  await debugPanel.getByText('调用 LLM').waitFor({ state: 'visible', timeout: 5000 })
  await debugPanel.getByText('RunID：preview-session-', { exact: false }).waitFor({ state: 'visible', timeout: 5000 })
  await debugPanel.getByText('服务端耗时', { exact: true }).waitFor({ state: 'visible', timeout: 5000 })
  const focusState = await debugPanel.evaluate((element) => document.activeElement === element)
  assert(focusState, 'Expected debug detail panel to receive focus when opened')

  await preview.getByRole('button', { name: '重置预览', exact: true }).click()
  await preview.getByText('发送一条消息，使用已保存 Agent 状态进行预览。').waitFor({ state: 'visible', timeout: 10000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent workbench preview e2e')
} finally {
  await browser.close()
}
