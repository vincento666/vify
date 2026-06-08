import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function portBox(page, selector) {
  return page.evaluate((portSelector) => {
    const element = document.querySelector(portSelector)
    if (!element) return null
    const box = element.getBoundingClientRect()
    const matrix = getComputedStyle(element).transform.match(/matrix\(([^,]+)/)
    const scale = matrix ? Number.parseFloat(matrix[1]) : 1
    return {
      width: box.width,
      height: box.height,
      centerX: box.left + box.width / 2,
      centerY: box.top + box.height / 2,
      scale,
    }
  }, selector)
}

function phaseScreenshotPath(name) {
  if (!screenshotPath) return ''
  const dot = screenshotPath.lastIndexOf('.')
  if (dot < 0) return `${screenshotPath}-${name}`
  return `${screenshotPath.slice(0, dot)}-${name}${screenshotPath.slice(dot)}`
}

async function maybeScreenshot(page, name) {
  const path = phaseScreenshotPath(name)
  if (path) await page.screenshot({ path, fullPage: true })
}

function closeToRatio(actual, expected, tolerance = 0.12) {
  return Math.abs(actual - expected) <= tolerance
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const chatflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `025.6 Endpoint Affordance ${Date.now()}`,
      description: 'endpoint affordance e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 220 } } } },
        { nodeKey: 'llm_1', type: 'LLM', name: '大模型', config: { outputVariable: 'answer', ui: { position: { x: 520, y: 220 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{llm_1.answer}}', ui: { position: { x: 920, y: 220 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
        { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create endpoint chatflow')

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  const node = page.locator('.vue-flow__node[data-id="llm_1"]')
  await node.waitFor({ state: 'visible', timeout: 5000 })
  const sourceSelector = '.vue-flow__node[data-id="llm_1"] .source-port'
  const targetSelector = '.vue-flow__node[data-id="llm_1"] .target-port'
  const defaultSource = await portBox(page, sourceSelector)
  const defaultTarget = await portBox(page, targetSelector)
  assert(defaultSource && defaultTarget, 'Expected source and target ports to render')
  await maybeScreenshot(page, 'default')

  await node.hover()
  await page.waitForTimeout(160)
  const nodeHoverSource = await portBox(page, sourceSelector)
  assert(closeToRatio(nodeHoverSource.scale, 2), `Expected node hover port scale 2x, got ${JSON.stringify(nodeHoverSource)}`)
  await maybeScreenshot(page, 'node-hover')

  const sourcePort = page.locator(sourceSelector)
  await sourcePort.hover({ force: true })
  await page.waitForTimeout(160)
  const endpointHoverSource = await portBox(page, sourceSelector)
  assert(closeToRatio(endpointHoverSource.scale, 3), `Expected endpoint hover scale 3x, got ${JSON.stringify(endpointHoverSource)}`)
  await maybeScreenshot(page, 'endpoint-hover')

  const defaultHoverRadius = defaultSource.width / 2
  await page.mouse.move(defaultSource.centerX + 42, defaultSource.centerY)
  await page.waitForTimeout(160)
  const radiusHoverSource = await portBox(page, sourceSelector)
  assert(
    closeToRatio(radiusHoverSource.scale, 3),
    `Expected endpoint hover radius to trigger 3x scale 42px from center, defaultRadius=${defaultHoverRadius}, got ${JSON.stringify(radiusHoverSource)}`,
  )
  await maybeScreenshot(page, 'endpoint-radius-hover')

  await node.click()
  await page.mouse.move(40, 40)
  await page.waitForTimeout(160)
  const selectedSource = await portBox(page, sourceSelector)
  assert(closeToRatio(selectedSource.scale, 1.2), `Expected selected node port scale 1.2x, got ${JSON.stringify(selectedSource)}`)
  await maybeScreenshot(page, 'selected')

  const selectedStyle = await page.evaluate(() => {
    const element = document.querySelector('.vue-flow__node[data-id="llm_1"] .coze-node')
    return element ? getComputedStyle(element).boxShadow : ''
  })
  assert(selectedStyle.includes('inset'), `Expected selected card to use an inset highlight, got ${selectedStyle}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS 025.6 endpoint affordances e2e chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
