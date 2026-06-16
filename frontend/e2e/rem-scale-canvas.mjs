import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_FRONTEND_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || ''

const routes = [
  { path: '/workflows/create', mode: 'workflow' },
  { path: '/chatflows/create', mode: 'chatflow' },
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
      await page.waitForSelector('[data-testid="workflow-canvas"]', { timeout: 20000 })
      await page.waitForSelector('.vue-flow__node', { timeout: 20000 })

      await page.locator('.vue-flow__node').first().click()
      await page.waitForSelector('[data-testid="node-config-panel"]', { timeout: 10000 })
      await page.getByRole('button', { name: '添加节点' }).click()
      await page.waitForSelector('[data-testid="bottom-node-palette"]', { timeout: 10000 })

      const snapshot = await page.evaluate(() => {
        const rootStyle = getComputedStyle(document.documentElement)
        const canvas = document.querySelector('[data-testid="workflow-canvas"]')?.getBoundingClientRect()
        const stage = document.querySelector('.canvas-stage-shell')?.getBoundingClientRect()
        const node = document.querySelector('.vue-flow__node')?.getBoundingClientRect()
        const panel = document.querySelector('[data-testid="node-config-panel"]')?.getBoundingClientRect()
        const palette = document.querySelector('[data-testid="bottom-node-palette"]')?.getBoundingClientRect()
        return {
          ready: document.documentElement.dataset.hifyUiScale,
          rootFont: Number.parseFloat(rootStyle.fontSize),
          scale: rootStyle.getPropertyValue('--hify-scale').trim(),
          nodeCount: document.querySelectorAll('.vue-flow__node').length,
          canvasWidth: canvas?.width ?? 0,
          canvasHeight: canvas?.height ?? 0,
          stageWidth: stage?.width ?? 0,
          nodeWidth: node?.width ?? 0,
          panelWidth: panel?.width ?? 0,
          paletteWidth: palette?.width ?? 0,
          overflowX: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
        }
      })

      const expectedRoot = width === 1280 ? 14 : 16
      const ok = snapshot.ready === 'ready'
        && Math.abs(snapshot.rootFont - expectedRoot) < 0.2
        && snapshot.nodeCount >= 2
        && snapshot.canvasWidth > 0
        && snapshot.canvasHeight > 0
        && snapshot.stageWidth > 0
        && snapshot.nodeWidth > 0
        && snapshot.panelWidth > 0
        && snapshot.paletteWidth > 0
        && snapshot.overflowX === 0

      if (!ok) failures.push({ route: route.path, width, snapshot })
      results.push({ route: route.path, width, ...snapshot })

      if (screenshotDir && width === 1280) {
        const name = route.path.replace(/\//g, '-').replace(/^-/, '')
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
