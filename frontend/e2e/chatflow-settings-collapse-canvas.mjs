import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function canvasGeometry(page) {
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
    const panel = rect('[data-testid="test-run-panel"]') || rect('[data-testid="node-config-panel"]')
    const availableRight = panel ? panel.left : window.innerWidth
    return {
      viewportWidth: window.innerWidth,
      availableRight,
      panel,
      toolbar: rect('[data-testid="canvas-bottom-toolbar"]'),
      start: rect('.vue-flow__node[data-id="start"]'),
      end: rect('.vue-flow__node[data-id="end"]'),
      stage: rect('.canvas-stage-shell'),
      resourcePanelDisplay: getComputedStyle(document.querySelector('.canvas-resource-panel') || document.body).display,
    }
  })
}

const browser = await chromium.launch()

try {
  const widePage = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await widePage.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  const sideToggle = widePage.getByRole('button', { name: '折叠侧栏', exact: true })
  await sideToggle.waitFor({ state: 'visible', timeout: 5000 })
  await sideToggle.click()
  await widePage.waitForTimeout(200)
  const wideGeometry = await canvasGeometry(widePage)
  assert(wideGeometry.stage?.width > 300, `Collapsed dialog settings must keep canvas stage visible, got ${JSON.stringify(wideGeometry)}`)
  assert(wideGeometry.start?.width > 20 && wideGeometry.end?.width > 20, `Collapsed dialog settings must keep nodes visible, got ${JSON.stringify(wideGeometry)}`)
  await widePage.close()

  const page = await browser.newPage({ viewport: { width: 877, height: 832 } })
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  const toolbar = page.getByTestId('canvas-bottom-toolbar')
  await toolbar.waitFor({ state: 'visible', timeout: 5000 })
  const testPanel = page.getByTestId('test-run-panel')
  if ((await testPanel.count()) === 0 || !(await testPanel.isVisible())) {
    await toolbar.getByRole('button', { name: '试运行', exact: true }).click()
    await testPanel.waitFor({ state: 'visible', timeout: 5000 })
  }
  const runHeaderStyle = await page.getByTestId('chatflow-run-fields-toggle').evaluate((element) => {
    const style = getComputedStyle(element)
    return {
      borderTopWidth: style.borderTopWidth,
      backgroundColor: style.backgroundColor,
      display: style.display,
      className: element.className,
      expanded: element.getAttribute('aria-expanded'),
    }
  })
  assert(runHeaderStyle.className.includes('section-title'), `Run parameter header must use section title styling, got ${JSON.stringify(runHeaderStyle)}`)
  assert(runHeaderStyle.borderTopWidth === '0px', `Run parameter header must not be a bordered card, got ${JSON.stringify(runHeaderStyle)}`)
  assert(runHeaderStyle.backgroundColor === 'rgba(0, 0, 0, 0)', `Run parameter header must stay transparent, got ${JSON.stringify(runHeaderStyle)}`)
  await page.waitForFunction(() => {
    const rect = (selector) => {
      const element = document.querySelector(selector)
      if (!element) return null
      return element.getBoundingClientRect()
    }
    const panel = rect('[data-testid="test-run-panel"]')
    const toolbar = rect('[data-testid="canvas-bottom-toolbar"]')
    const end = rect('.vue-flow__node[data-id="end"]')
    if (!panel || !toolbar || !end) return false
    const endCenter = end.left + end.width / 2
    return toolbar.left >= 0 && endCenter < panel.left - 8
  }, null, { timeout: 3000 })

  const geometry = await canvasGeometry(page)
  assert(geometry.resourcePanelDisplay === 'none', `Expected compact canvas to hide/collapse dialog settings panel, got ${JSON.stringify(geometry)}`)
  assert(geometry.toolbar, `Missing toolbar geometry ${JSON.stringify(geometry)}`)
  assert(geometry.toolbar.left >= 0, `Toolbar must stay in the visible canvas, got ${JSON.stringify(geometry)}`)
  assert(geometry.start && geometry.end, `Missing start/end nodes ${JSON.stringify(geometry)}`)

  for (const [name, box] of Object.entries({ start: geometry.start, end: geometry.end })) {
    const centerX = box.left + box.width / 2
    assert(centerX > 0, `${name} node must stay inside the left viewport, got ${JSON.stringify(geometry)}`)
    assert(
      centerX < geometry.availableRight - 8,
      `${name} node must not be hidden behind the right run panel, got ${JSON.stringify(geometry)}`,
    )
  }

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow settings collapse canvas e2e')
} finally {
  await browser.close()
}
