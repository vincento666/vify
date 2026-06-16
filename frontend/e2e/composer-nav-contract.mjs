import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/provider`, { waitUntil: 'networkidle' })
  const sidebar = page.locator('.sidebar-nav')
  await sidebar.getByText('工作流', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await sidebar.getByText('Agent', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await sidebar.getByText('评测', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })

  const observeCount = await sidebar.getByText('观测', { exact: true }).count()
  assert(observeCount === 0, 'Expected Coze composer mode to remove top-level Observe navigation')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS composer navigation contract e2e')
} finally {
  await browser.close()
}
