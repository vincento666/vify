import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-end').click()
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const editor = panel.getByTestId('config-section-回答内容').getByTestId('end-answer-content-editor')
  await editor.waitFor({ state: 'visible', timeout: 5000 })

  assert(await editor.getByRole('button', { name: '插入响应变量', exact: true }).count() === 0, 'END response must not expose a variable button')
  assert(await editor.getByRole('button', { name: '变量', exact: true }).count() === 0, 'END response must not expose visible variable copy button')

  const responseInput = editor.locator('textarea[aria-label="回答内容"]')
  await responseInput.fill('{')
  assert(await responseInput.inputValue() === '{{}}', 'Typing { should auto-complete to {{}}')

  const picker = editor.getByTestId('variable-picker')
  await picker.waitFor({ state: 'visible', timeout: 5000 })
  assert(await picker.getAttribute('data-picker-kind') === 'inline', 'Inline text variables should use the compact suggestion picker')
  const pickerText = await picker.innerText()
  assert(pickerText.includes('output'), `Inline picker should expose local END output variable, got ${pickerText}`)
  assert(!pickerText.includes('{{'), `Inline picker must show compact variable labels instead of raw references, got ${pickerText}`)
  assert(!pickerText.includes('sys.query'), `Inline picker must not expose undeclared system variables directly, got ${pickerText}`)
  await picker.getByTestId('variable-option').filter({ hasText: 'output' }).click()

  const value = await responseInput.inputValue()
  assert(value.includes('{{output}}'), `Expected selected local variable to replace {{}}, got ${value}`)
  assert(!value.includes('{{}}'), `Expected placeholder braces to be replaced, got ${value}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow inline variable trigger e2e')
} finally {
  await browser.close()
}
