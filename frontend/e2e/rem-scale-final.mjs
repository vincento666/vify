import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_FRONTEND_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || ''

const widths = [900, 1280, 1440, 1920, 2560]
const routes = [
  { path: '/provider', selector: '.page-container' },
  { path: '/agent', selector: '.page-container' },
  { path: '/agents/new', selector: '[data-testid="agent-workbench-shell"]' },
  { path: '/chat', selector: '.chat-layout' },
  { path: '/knowledge', selector: '.page-container' },
  { path: '/workflows', selector: '.workflow-list' },
  { path: '/workflows/create', selector: '[data-testid="workflow-canvas"]', waitFor: '.vue-flow__node' },
  { path: '/chatflows/create', selector: '[data-testid="workflow-canvas"]', waitFor: '.vue-flow__node' },
  { path: '/evaluation', selector: '.evaluation-page' },
  { path: '/mcp', selector: '.page-container' },
]

function expectedRootFont(width) {
  const minWidth = 1280
  const baseWidth = 1920
  const maxWidth = 3840
  const clamped = Math.min(maxWidth, Math.max(minWidth, width))
  let scale
  if (clamped <= baseWidth) {
    const progress = (clamped - minWidth) / (baseWidth - minWidth)
    scale = 0.875 + (1 - 0.875) * progress
  } else {
    const progress = (clamped - baseWidth) / (maxWidth - baseWidth)
    scale = 1 + (1.5 - 1) * progress
  }
  return Number((16 * scale).toFixed(4))
}

const browser = await chromium.launch({ headless: true })
const failures = []
const results = []

for (const route of routes) {
  for (const width of widths) {
    const page = await browser.newPage({ viewport: { width, height: 900 }, deviceScaleFactor: 1 })
    try {
      await page.goto(`${baseUrl}${route.path}`, { waitUntil: 'networkidle' })
      await page.waitForSelector(route.selector, { timeout: 20000 })
      if (route.waitFor) await page.waitForSelector(route.waitFor, { timeout: 20000 })

      const snapshot = await page.evaluate((selector) => {
        const rootStyle = getComputedStyle(document.documentElement)
        const target = document.querySelector(selector)?.getBoundingClientRect()
        return {
          ready: document.documentElement.dataset.hifyUiScale,
          rootFont: Number.parseFloat(rootStyle.fontSize),
          scale: rootStyle.getPropertyValue('--hify-scale').trim(),
          targetWidth: target?.width ?? 0,
          targetHeight: target?.height ?? 0,
          bodyTextLength: document.body.innerText.trim().length,
          overflowX: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
        }
      }, route.selector)

      const expectedRoot = expectedRootFont(width)
      const ok = snapshot.ready === 'ready'
        && Math.abs(snapshot.rootFont - expectedRoot) < 0.25
        && snapshot.targetWidth > 0
        && snapshot.targetHeight > 0
        && snapshot.bodyTextLength > 0
        && snapshot.overflowX === 0

      if (!ok) failures.push({ route: route.path, width, expectedRoot, snapshot })
      results.push({ route: route.path, width, expectedRoot, ...snapshot })

      if (screenshotDir && [900, 1920].includes(width)) {
        const name = route.path.replace(/\//g, '-').replace(/^-/, '') || 'root'
        await page.screenshot({ path: `${screenshotDir}/${name}-${width}.png`, fullPage: true })
      }
    } catch (error) {
      failures.push({ route: route.path, width, error: error instanceof Error ? error.message : String(error) })
    } finally {
      await page.close()
    }
  }
}

await browser.close()

console.log(JSON.stringify({ baseUrl, widths, routes: routes.map((route) => route.path), results, failures }, null, 2))

if (failures.length > 0) {
  process.exit(1)
}
