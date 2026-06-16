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

async function firstEnabledModel(page) {
  const providers = await unwrap(await page.request.get(`${baseUrl}/api/v1/providers?page=1&pageSize=100&enabled=true`), 'list providers')
  for (const provider of providers.list) {
    for (const model of provider.models || []) {
      if (model.enabled) return model.id
    }
  }
  throw new Error('No enabled model config available for agent preview debug e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1500, height: 920 } })

try {
  const stamp = Date.now()
  const modelConfigId = await firstEnabledModel(page)
  const agent = await unwrap(await page.request.post(`${baseUrl}/api/v1/agents`, {
    data: {
      name: `021.4 Agent Preview Debug ${stamp}`,
      description: '',
      systemPrompt: 'Answer briefly and mention preview debug.',
      modelConfigId,
      temperature: 0.2,
      maxTokens: 256,
      maxContextTurns: 4,
      toolIds: [],
      openingMessage: '你好，我是预览调试助手。',
      suggestedQuestions: ['如何开始？'],
    },
  }), 'create agent')
  const session = await unwrap(await page.request.post(`${baseUrl}/api/v1/chat/sessions`, {
    data: { agentId: agent.id },
  }), 'create preview session')
  await unwrap(await page.request.post(`${baseUrl}/api/v1/chat/sessions/${session.id}/messages`, {
    data: { content: 'preview debug smoke', stream: false, variables: {} },
  }), 'send preview message')

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench?previewRunId=${session.id}&debug=1`, { waitUntil: 'networkidle' })
  const panel = page.getByTestId('agent-debug-detail-panel')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  const text = await panel.innerText()
  const shell = page.locator('[data-testid="agent-workbench-shell"]')
  const gridWidth = await shell.evaluate((element) => element.scrollWidth)
  const viewportWidth = await shell.evaluate((element) => element.clientWidth)
  const headerWidth = await page.locator('.workbench-header').evaluate((element) => element.getBoundingClientRect().width)
  const saveButtonWidth = await page.getByRole('button', { name: '保存配置' }).evaluate((element) => element.getBoundingClientRect().width)
  const publishButtonWidth = await page.getByRole('button', { name: '发布' }).evaluate((element) => element.getBoundingClientRect().width)

  assert(page.url().includes(`/agents/${agent.id}/workbench`), `Expected agent workbench URL, got ${page.url()}`)
  assert(text.includes(`RunID：${session.id}`), `Expected previewRunId in debug panel, got ${text}`)
  assert(text.includes('preview debug smoke'), 'Expected user input keyword in debug panel')
  assert(text.includes('调用树'), 'Expected call tree tab')
  assert(text.includes('火焰图'), 'Expected flamegraph tab')
  assert(text.includes('用户输入'), 'Expected user input node')
  assert(text.includes('调用 LLM'), 'Expected LLM node')
  assert(gridWidth > viewportWidth, `Expected four-column horizontal scroll, got scrollWidth=${gridWidth} viewport=${viewportWidth}`)
  assert(headerWidth > viewportWidth, `Expected header to expand with debug columns, got headerWidth=${headerWidth} viewport=${viewportWidth}`)
  assert(saveButtonWidth >= 80, `Expected save button not compressed, got width=${saveButtonWidth}`)
  assert(publishButtonWidth >= 52, `Expected publish button not compressed, got width=${publishButtonWidth}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS agent preview run debug deeplink agent=${agent.id} previewRun=${session.id}`)
} finally {
  await browser.close()
}
