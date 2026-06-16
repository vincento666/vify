import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByRole('heading', { name: '客服助手' }).waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.sidebar-nav').getByText('客服助手', { exact: true }).waitFor({
    state: 'visible',
    timeout: 10000,
  })

  const metrics = await page.evaluate(() => ({
    path: window.location.pathname,
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    titleCount: document.querySelectorAll('h1').length,
  }))

  assert(metrics.path === '/customer-assistant', `Expected /customer-assistant, got ${metrics.path}`)
  assert(metrics.titleCount === 1, `Expected one module heading, got ${metrics.titleCount}`)
  assert(metrics.overflowX <= 0, `Expected no horizontal overflow, got ${metrics.overflowX}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant route contract e2e')
} finally {
  await browser.close()
}
