import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '试运行' }).click()

  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByText('校验失败').waitFor({ state: 'visible', timeout: 5000 })
  const validationText = await panel.innerText()
  assert(
    validationText.includes('START must connect to END through at least one path'),
    'Expected disconnected graph to fail validation before a test run',
  )

  await page.getByRole('button', { name: '快速连线' }).click()
  await panel.getByPlaceholder('输入 userMessage').fill('hello from e2e')
  await panel.getByRole('button', { name: '运行', exact: true }).click()
  await page.waitForURL('**/workflows/*/canvas', { timeout: 10000 })

  const result = panel.locator('.run-result')
  await result.waitFor({ state: 'visible', timeout: 10000 })
  const resultText = await result.innerText()
  assert(resultText.includes('"status": "SUCCEEDED"'), 'Expected successful workflow test run status')
  assert(resultText.includes('"output"'), 'Expected workflow test run output payload')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow test run e2e')
} finally {
  await browser.close()
}
