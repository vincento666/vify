import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Chatflow Variables ${Date.now()}`

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('Chatflow 名称').fill(name)

  const variablePanel = page.locator('[data-testid="chatflow-variable-panel"]')
  await variablePanel.waitFor({ state: 'visible', timeout: 5000 })
  const panelText = await variablePanel.innerText()
  for (const scope of ['System', 'Global', 'Conversation', 'User', 'Channel', 'External Input']) {
    assert(panelText.includes(scope), `Expected variable panel to include scope ${scope}`)
  }

  await variablePanel.locator('button', { hasText: '{{sys.query}}' }).click()
  const configPanel = page.locator('[data-testid="node-config-panel"]')
  await configPanel.waitFor({ state: 'visible', timeout: 5000 })
  const template = await configPanel.getByPlaceholder('返回给调用方的文本，可使用变量引用').inputValue()
  assert(template.includes('{{sys.query}}'), 'Expected variable selector to insert sys.query')

  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForURL('**/chatflows/*/canvas', { timeout: 10000 })
  await page.reload({ waitUntil: 'networkidle' })

  await page.locator('.coze-node', { hasText: '结束' }).click()
  await configPanel.waitFor({ state: 'visible', timeout: 5000 })
  const reopenedTemplate = await configPanel.getByPlaceholder('返回给调用方的文本，可使用变量引用').inputValue()
  assert(reopenedTemplate.includes('{{sys.query}}'), 'Expected inserted variable to persist after reopen')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow variable selector e2e')
} finally {
  await browser.close()
}
