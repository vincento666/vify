import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Chatflow Run ${Date.now()}`

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('Chatflow 名称').fill(name)
  await page.locator('.coze-node', { hasText: '结束' }).click()
  const configPanel = page.locator('[data-testid="node-config-panel"]')
  await configPanel.waitFor({ state: 'visible', timeout: 5000 })
  await configPanel
    .getByPlaceholder('返回给调用方的文本，可使用变量引用')
    .fill('机器人收到 {{sys.query}} via {{sys.channel}} for {{global.brand}}/{{global.locale}}')

  await page.getByRole('button', { name: '对话试运行' }).click()
  const testPanel = page.locator('[data-testid="test-run-panel"]')
  await testPanel.waitFor({ state: 'visible', timeout: 5000 })
  await testPanel.getByPlaceholder('输入用户消息').fill('查订单')
  await testPanel.getByPlaceholder('conversation_id').fill('conv-e2e')
  await testPanel.getByPlaceholder('user_id').fill('user-e2e')
  await testPanel.getByRole('button', { name: '运行', exact: true }).click()
  await page.waitForURL('**/chatflows/*/canvas', { timeout: 10000 })
  await testPanel.getByTestId('chatflow-assistant-message').waitFor({ state: 'visible', timeout: 10000 })

  const assistantText = await testPanel.getByTestId('chatflow-assistant-message').innerText()
  assert(
    assistantText.includes('机器人收到 查订单 via web for Hify/zh-CN'),
    `Expected assistant-style output to render sys variables, got: ${assistantText}`,
  )

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow conversation run e2e')
} finally {
  await browser.close()
}
