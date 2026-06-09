import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Chatflow Shared Picker ${Date.now()}`

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('Chatflow 名称').fill(name)
  await page.locator('.coze-node.node-end').click()

  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const answerSection = panel.getByTestId('config-section-回答内容')
  const responseInput = answerSection.getByLabel('回答内容')
  await responseInput.fill('{')

  const picker = page.locator('[data-testid="variable-picker"]')
  await picker.waitFor({ state: 'visible', timeout: 5000 })
  const pickerText = await picker.innerText()
  assert(pickerText.includes('sys.query'), `Expected END answer content to expose upstream system query, got ${pickerText}`)
  assert(pickerText.includes('sys.conversation_id'), `Expected END answer content to expose upstream conversation id, got ${pickerText}`)
  assert(!pickerText.includes('{{'), `Inline picker must show compact variable labels instead of raw references, got ${pickerText}`)
  await picker.locator('[data-testid="variable-option"]', { hasText: 'sys.query' }).click()

  const template = await responseInput.inputValue()
  assert(template.includes('{{start.sys.query}}'), 'Expected shared picker to insert upstream system query reference')

  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForURL('**/chatflows/*/canvas', { timeout: 10000 })
  await page.reload({ waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-end').click()
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const reopenedTemplate = await panel.getByPlaceholder('返回给调用方的文本，可使用变量引用').inputValue()
  assert(reopenedTemplate.includes('{{start.sys.query}}'), 'Expected upstream system query reference to persist')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow shared variable picker e2e')
} finally {
  await browser.close()
}
