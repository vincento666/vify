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
  await page.getByRole('button', { name: '试运行', exact: true }).first().click()

  const dock = page.getByTestId('workflow-debug-dock')
  await dock.waitFor({ state: 'visible', timeout: 5000 })
  const dockText = await dock.innerText()
  assert(dockText.includes('错误列表'), `Expected error list dock, got ${dockText}`)
  assert(dockText.includes('START must connect to END'), `Expected graph validation error, got ${dockText}`)
  assert(await page.getByTestId('test-run-panel').count() === 0, 'Invalid graph must not open test-run panel')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow run validation errors e2e')
} finally {
  await browser.close()
}
