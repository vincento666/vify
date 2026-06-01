import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const workflowScreenshotPath = process.env.HIFY_E2E_WORKFLOW_SCREENSHOT
const chatflowScreenshotPath = process.env.HIFY_E2E_CHATFLOW_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function addAndConfigureLlm(page, prompt) {
  await page.getByRole('button', { name: '添加节点' }).click()
  await page.locator('.node-palette button', { hasText: '大模型' }).click()
  await page.locator('.vue-flow__node[data-id="llm_1"]').waitFor({ state: 'visible', timeout: 5000 })
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()

  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.locator('textarea').fill(prompt)
  await panel.getByLabel('关闭配置').click()

  await page.locator('.vue-flow__node[data-id="end"]').click()
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByPlaceholder('返回给调用方的文本，可使用变量引用').fill('{{llm_1.output}}')
  await page.getByRole('button', { name: '快速连线' }).click()
}

async function runWorkflowUat(page) {
  const marker = `workflow-llm-${Date.now()}`
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('工作流名称').fill(`Workflow LLM UAT ${marker}`)
  await addAndConfigureLlm(page, `Workflow LLM UAT {{start.USER_INPUT}}`)

  await page.getByRole('button', { name: '试运行' }).click()
  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByPlaceholder('输入 userMessage').fill(marker)
  await panel.getByRole('button', { name: '运行', exact: true }).click()
  await page.waitForURL('**/workflows/*/canvas', { timeout: 10000 })

  const output = page.locator('[data-testid="workflow-run-output"]')
  await output.waitFor({ state: 'visible', timeout: 10000 })
  const outputText = await output.innerText()
  const panelText = await panel.innerText()
  assert(panelText.includes('SUCCEEDED'), 'Expected workflow LLM test run to succeed')
  assert(outputText.includes(`LLM mock: Workflow LLM UAT ${marker}`), `Expected workflow LLM output, got: ${outputText}`)
  assert(await panel.locator('.run-result').count() === 0, 'Expected workflow run panel to omit raw JSON code block')
  if (workflowScreenshotPath) {
    await page.screenshot({ path: workflowScreenshotPath, fullPage: true })
  }
}

async function runChatflowUat(page) {
  const marker = `chatflow-llm-${Date.now()}`
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('Chatflow 名称').fill(`Chatflow LLM UAT ${marker}`)
  await addAndConfigureLlm(page, 'Chatflow LLM UAT {{sys.query}} via {{sys.channel}}')

  await page.getByRole('button', { name: '对话试运行' }).click()
  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByPlaceholder('输入用户消息').fill(marker)
  await panel.getByRole('button', { name: '运行', exact: true }).click()
  await page.waitForURL('**/chatflows/*/canvas', { timeout: 10000 })

  const assistant = page.locator('.message-bubble.assistant')
  await assistant.waitFor({ state: 'visible', timeout: 10000 })
  const assistantText = await assistant.innerText()
  const panelText = await panel.innerText()
  assert(panelText.includes('SUCCEEDED'), 'Expected chatflow LLM test run to succeed')
  assert(assistantText.includes(`LLM mock: Chatflow LLM UAT ${marker} via web`), `Expected chatflow LLM output, got: ${assistantText}`)
  assert(await panel.locator('.run-result').count() === 0, 'Expected chatflow run panel to omit raw JSON code block')
  if (chatflowScreenshotPath) {
    await page.screenshot({ path: chatflowScreenshotPath, fullPage: true })
  }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await runWorkflowUat(page)
  await runChatflowUat(page)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow/chatflow LLM canvas run e2e')
} finally {
  await browser.close()
}
