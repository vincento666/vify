import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Chatflow Publish ${Date.now()}`

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('Chatflow 名称').fill(name)
  await page.locator('.coze-node', { hasText: '结束' }).click()
  const configPanel = page.locator('[data-testid="node-config-panel"]')
  await configPanel.waitFor({ state: 'visible', timeout: 5000 })
  await configPanel.getByPlaceholder('返回给调用方的文本，可使用变量引用').fill('发布测试 {{sys.query}}')

  await page.getByRole('button', { name: '发布', exact: true }).click()
  const opsPanel = page.locator('[data-testid="workflow-ops-panel"]')
  await opsPanel.waitFor({ state: 'visible', timeout: 5000 })
  let panelText = await opsPanel.innerText()
  assert(panelText.includes('需要先完成一次成功试运行'), 'Expected publish gate to block before test run')
  await opsPanel.getByRole('button', { name: 'Open API' }).click()
  panelText = await opsPanel.innerText()
  assert(panelText.includes('/api/v1/chatflows/'), 'Expected operations panel to expose Chatflow Open API endpoint')

  await page.getByRole('button', { name: '对话试运行' }).click()
  const testPanel = page.locator('[data-testid="test-run-panel"]')
  await testPanel.waitFor({ state: 'visible', timeout: 5000 })
  await testPanel.getByPlaceholder('输入用户消息').fill('hello publish')
  await testPanel.getByRole('button', { name: '运行', exact: true }).click()
  await page.waitForURL('**/chatflows/*/canvas', { timeout: 10000 })
  await page.locator('.message-bubble.assistant').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('button', { name: '发布', exact: true }).click()
  await opsPanel.waitFor({ state: 'visible', timeout: 5000 })
  panelText = await opsPanel.innerText()
  assert(panelText.includes('SUCCEEDED'), 'Expected publish panel to show successful run status')

  await opsPanel.getByRole('button', { name: '确认发布' }).click()
  await opsPanel.getByText('PUBLISHED').waitFor({ state: 'visible', timeout: 10000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow publish/open shell e2e')
} finally {
  await browser.close()
}
