import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const shotPath = process.env.HIFY_E2E_SCREENSHOT
  || '/Users/vincento/work/develop/hify/artifacts/slices/212-runtime-baseline-lock-and-regression-gate/212.8/screenshots/green-conversation-run.png'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Chatflow UAT ${Date.now()}`

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
  await testPanel.getByTestId('chatflow-run-fields-toggle').click()
  await testPanel.getByPlaceholder('发送消息').fill('查订单')
  await testPanel.getByPlaceholder('conversation_id').fill('conv-e2e')
  await testPanel.getByPlaceholder('user_id').fill('user-e2e')
  await testPanel.getByRole('button', { name: '发送消息', exact: true }).click()
  await page.waitForURL('**/chatflows/*/canvas', { timeout: 10000 })
  await testPanel.getByTestId('chatflow-assistant-message').waitFor({ state: 'visible', timeout: 15000 })
  await page.waitForTimeout(300)
  const txt = await testPanel.getByTestId('chatflow-assistant-message').innerText()
  console.log('FINAL_TEXT:', JSON.stringify(txt))
  await page.screenshot({ path: shotPath, fullPage: true })
  console.log('SAVED:', shotPath)
} finally {
  await browser.close()
}
