import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function boxes(page) {
  return page.evaluate(() => {
    const rect = (selector) => {
      const element = document.querySelector(selector)
      if (!element) return null
      const box = element.getBoundingClientRect()
      return {
        left: box.left,
        right: box.right,
        top: box.top,
        bottom: box.bottom,
        width: box.width,
        height: box.height,
      }
    }
    return {
      canvas: rect('[data-testid="workflow-canvas"]'),
      toolbar: rect('[data-testid="canvas-bottom-toolbar"]'),
      config: rect('[data-testid="node-config-panel"]'),
      testRun: rect('[data-testid="test-run-panel"]'),
      debug: rect('[data-testid="workflow-debug-dock"]'),
    }
  })
}

async function assertLayout(page, path) {
  await page.goto(`${baseUrl}${path}`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="end"]').click()
  await page.getByTestId('node-config-panel').waitFor({ state: 'visible', timeout: 5000 })
  await page.getByRole('button', { name: '调试工具', exact: true }).click()
  await page.getByTestId('workflow-debug-dock').waitFor({ state: 'visible', timeout: 5000 })

  let geometry = await boxes(page)
  assert(geometry.canvas && geometry.toolbar && geometry.config && geometry.debug, `Missing config geometry ${JSON.stringify(geometry)}`)

  const availableLeft = geometry.canvas.left
  const availableRight = geometry.debug.right
  const visibleCenter = (availableLeft + availableRight) / 2
  const toolbarCenter = geometry.toolbar.left + geometry.toolbar.width / 2
  assert(Math.abs(toolbarCenter - visibleCenter) <= 3, `Toolbar center ${toolbarCenter} must match visible center ${visibleCenter}`)
  assert(geometry.debug.right <= geometry.config.left - 8, `Debug dock overlaps config panel ${JSON.stringify(geometry)}`)
  assert(Math.abs((geometry.config.top - geometry.canvas.top) - geometry.debug.left) <= 2, `Config panel top gap must align with debug dock side gap inside the canvas stage ${JSON.stringify(geometry)}`)
  assert(Math.abs((page.viewportSize().width - geometry.config.right) - geometry.debug.left) <= 2, `Config panel right gap must align with debug dock side gap ${JSON.stringify(geometry)}`)
  assert(Math.abs((page.viewportSize().height - geometry.config.bottom) - geometry.debug.left) <= 2, `Config panel bottom gap must align with debug dock bottom gap ${JSON.stringify(geometry)}`)

  await page.getByRole('button', { name: /试运行|对话试运行/ }).first().click()
  await page.getByTestId('test-run-panel').waitFor({ state: 'visible', timeout: 5000 })
  geometry = await boxes(page)
  assert(geometry.canvas && geometry.toolbar && geometry.testRun && geometry.debug, `Missing trial geometry ${JSON.stringify(geometry)}`)
  assert(geometry.debug.right <= geometry.testRun.left - 8, `Debug dock overlaps trial panel ${JSON.stringify(geometry)}`)
  assert(Math.abs(geometry.debug.bottom - geometry.testRun.bottom) <= 2, `Trial bottom must align with debug dock ${JSON.stringify(geometry)}`)
  assert(Math.abs((geometry.testRun.top - geometry.canvas.top) - geometry.debug.left) <= 2, `Trial panel top gap must align with debug dock side gap inside the canvas stage ${JSON.stringify(geometry)}`)
  assert(Math.abs((page.viewportSize().width - geometry.testRun.right) - geometry.debug.left) <= 2, `Trial panel right gap must align with debug dock side gap ${JSON.stringify(geometry)}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await assertLayout(page, '/chatflows/create')
  await assertLayout(page, '/workflows/create')
  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log('PASS workflow/chatflow layout polish')
} finally {
  await browser.close()
}
