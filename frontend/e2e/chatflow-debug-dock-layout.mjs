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
  await page.locator('.vue-flow__node[data-id="end"]').click()
  const configPanel = page.getByTestId('node-config-panel')
  await configPanel.waitFor({ state: 'visible', timeout: 5000 })
  await page.getByRole('button', { name: '调试工具', exact: true }).click()
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.waitFor({ state: 'visible', timeout: 5000 })

  const boxes = await page.evaluate(() => {
    const config = document.querySelector('[data-testid="node-config-panel"]')?.getBoundingClientRect()
    const debug = document.querySelector('[data-testid="workflow-debug-dock"]')?.getBoundingClientRect()
    return {
      config: config ? { left: config.left, right: config.right, top: config.top, bottom: config.bottom } : null,
      debug: debug ? { left: debug.left, right: debug.right, top: debug.top, bottom: debug.bottom } : null,
    }
  })
  assert(boxes.config && boxes.debug, `Expected config panel and debug dock boxes, got ${JSON.stringify(boxes)}`)
  assert(boxes.debug.right <= boxes.config.left - 8, `Debug dock must not overlap config panel, got ${JSON.stringify(boxes)}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow debug dock layout e2e')
} finally {
  await browser.close()
}
