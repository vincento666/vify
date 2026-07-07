import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function withHostContext(path, context) {
  return `${baseUrl}${path}?hifyHostContext=${encodeURIComponent(JSON.stringify(context))}`
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(withHostContext('/runtime-ops', { permissions: ['runtime_ops:read'] }), { waitUntil: 'networkidle' })
  await page.getByTestId('runtime-ops-shell').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('link', { name: /运行观测/ }).waitFor({ state: 'visible', timeout: 10000 })
  const heading = await page.getByRole('heading', { name: '运行观测' }).textContent()
  assert(heading === '运行观测', `Expected runtime ops heading, got ${heading}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  await page.goto(withHostContext('/runtime-ops', { permissions: ['workflow:run'] }), { waitUntil: 'networkidle' })
  await page.waitForURL(/\/provider\?denied=HifyRuntimeOps/, { timeout: 10000 })
  const deniedLinkCount = await page.getByRole('link', { name: /运行观测/ }).count()
  assert(deniedLinkCount === 0, 'Runtime ops nav item should be hidden when host permissions exclude runtime_ops:read')

  console.log('PASS runtime ops entry route and permission gate')
} finally {
  await browser.close()
}
