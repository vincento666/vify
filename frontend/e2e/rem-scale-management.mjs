import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_FRONTEND_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || ''

const routes = [
  { path: '/provider', selector: '.page-container' },
  { path: '/agent', selector: '.page-container' },
  { path: '/knowledge', selector: '.page-container' },
  { path: '/mcp', selector: '.page-container' },
  { path: '/workflows', selector: '.workflow-list' },
  { path: '/chatflows', selector: '.chatflow-list' },
  { path: '/evaluation', selector: '.evaluation-page' },
]

const widths = [1280, 1920]
const browser = await chromium.launch({ headless: true })
const failures = []
const results = []

for (const route of routes) {
  for (const width of widths) {
    const page = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: 1 })
    try {
      await page.goto(`${baseUrl}${route.path}`, { waitUntil: 'networkidle' })
      await page.waitForSelector(route.selector, { timeout: 15000 })

      const snapshot = await page.evaluate((selector) => {
        const rootStyle = getComputedStyle(document.documentElement)
        const target = document.querySelector(selector)
        const rect = target?.getBoundingClientRect()
        return {
          ready: document.documentElement.dataset.hifyUiScale,
          rootFont: Number.parseFloat(rootStyle.fontSize),
          scale: rootStyle.getPropertyValue('--hify-scale').trim(),
          bodyTextLength: document.body.innerText.trim().length,
          targetWidth: rect?.width ?? 0,
          targetHeight: rect?.height ?? 0,
          overflowX: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
        }
      }, route.selector)

      const expectedRoot = width === 1280 ? 14 : 16
      const ok = snapshot.ready === 'ready'
        && Math.abs(snapshot.rootFont - expectedRoot) < 0.2
        && snapshot.bodyTextLength > 0
        && snapshot.targetWidth > 0
        && snapshot.targetHeight > 0
        && snapshot.overflowX === 0

      if (!ok) failures.push({ route: route.path, width, snapshot })
      results.push({ route: route.path, width, ...snapshot })

      if (screenshotDir && width === 1280) {
        const name = route.path.replace(/\//g, '-').replace(/^-/, '') || 'root'
        await page.screenshot({ path: `${screenshotDir}/${name}-1280.png`, fullPage: true })
      }
    } catch (error) {
      failures.push({ route: route.path, width, error: error instanceof Error ? error.message : String(error) })
    } finally {
      await page.close()
    }
  }
}

await browser.close()

console.log(JSON.stringify({ baseUrl, results, failures }, null, 2))

if (failures.length > 0) {
  process.exit(1)
}
