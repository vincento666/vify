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
    const pane = document.querySelector('.vue-flow__transformationpane')
    const box = element.getBoundingClientRect()
    const matrixScale = (value) => {
      const matrix = String(value || '').match(/matrix\(([^,]+)/)
      return matrix ? Number.parseFloat(matrix[1]) : 1
    }
    const handleStyle = getComputedStyle(element)
    const hitStyle = getComputedStyle(element, '::before')
    const dotStyle = getComputedStyle(element, '::after')
    const paneScale = matrixScale(pane ? getComputedStyle(pane).transform : '')
    const dotWidth = Number.parseFloat(dotStyle.width || '0')
    const dotScale = matrixScale(dotStyle.transform)
    return {
      width: box.width,
      height: box.height,
      cssWidth: Number.parseFloat(handleStyle.width),
      cssHeight: Number.parseFloat(handleStyle.height),
      dotWidth: dotStyle.width,
      dotHeight: dotStyle.height,
      hitWidth: hitStyle.width,
      hitHeight: hitStyle.height,
      centerX: box.left + box.width / 2,
      centerY: box.top + box.height / 2,
      handleScale: matrixScale(handleStyle.transform),
      dotScale,
      paneScale,
      screenDotWidth: dotWidth * paneScale * dotScale,
    }
  }, selector)
}

async function nodeBox(page, selector) {
  return page.evaluate((nodeSelector) => {
    const node = document.querySelector(nodeSelector)
    if (!node) return null
    const box = node.getBoundingClientRect()
    return {
      left: box.left,
      right: box.right,
      centerY: box.top + box.height / 2,
    }
  }, selector)
}

async function rootFontSize(page) {
  return page.evaluate(() => Number.parseFloat(getComputedStyle(document.documentElement).fontSize))
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

function assertClose(actual, expected, tolerance, message) {
  assert(Math.abs(actual - expected) <= tolerance, `${message}: expected ${expected}, got ${actual}`)
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
  const nodeSelector = '.vue-flow__node[data-id="llm_1"] .coze-node'
  const sourceSelector = '.vue-flow__node[data-id="llm_1"] .source-port'
  const targetSelector = '.vue-flow__node[data-id="llm_1"] .target-port'
  const defaultNode = await nodeBox(page, nodeSelector)
  const defaultSource = await portBox(page, sourceSelector)
  const defaultTarget = await portBox(page, targetSelector)
  const rem = await rootFontSize(page)
  const expectedBaseDiameter = 1 * rem
  const expectedHitDiameter = 3 * rem
  assert(defaultNode && defaultSource && defaultTarget, 'Expected node source and target ports to render')
  assertClose(defaultSource.cssWidth, expectedBaseDiameter, 1, `Expected endpoint handle box to match the visible dot so edges anchor to the dot, got ${JSON.stringify(defaultSource)}`)
  assertClose(defaultTarget.cssWidth, expectedBaseDiameter, 1, `Expected target handle box to match the visible dot so edges anchor to the dot, got ${JSON.stringify(defaultTarget)}`)
  assertClose(Number.parseFloat(defaultSource.hitWidth || '0'), expectedHitDiameter, 1, `Expected endpoint hover hit area to keep the 3x radius without changing edge anchors, got ${JSON.stringify(defaultSource)}`)
  assertClose(Number.parseFloat(defaultTarget.hitWidth || '0'), expectedHitDiameter, 1, `Expected target hover hit area to keep the 3x radius without changing edge anchors, got ${JSON.stringify(defaultTarget)}`)
  assert(Math.abs(defaultSource.centerX - defaultNode.right) <= 1, `Expected source port center to align with node right edge, got node=${JSON.stringify(defaultNode)} source=${JSON.stringify(defaultSource)}`)
  assert(Math.abs(defaultTarget.centerX - defaultNode.left) <= 1, `Expected target port center to align with node left edge, got node=${JSON.stringify(defaultNode)} target=${JSON.stringify(defaultTarget)}`)
  await maybeScreenshot(page, 'default')

  await node.hover()
  await page.waitForTimeout(160)
  const nodeHoverSource = await portBox(page, sourceSelector)
  assert(closeToRatio(nodeHoverSource.width, defaultSource.width, 0.5), `Expected node hover hit box to keep the original 1x size, got default=${JSON.stringify(defaultSource)} hover=${JSON.stringify(nodeHoverSource)}`)
  assert(closeToRatio(nodeHoverSource.dotScale, 2), `Expected node hover port dot scale 2x, got ${JSON.stringify(nodeHoverSource)}`)
  await maybeScreenshot(page, 'node-hover')

  const sourcePort = page.locator(sourceSelector)
  await sourcePort.hover({ force: true })
  await page.waitForTimeout(160)
  const endpointHoverSource = await portBox(page, sourceSelector)
  assert(closeToRatio(endpointHoverSource.width, defaultSource.width, 0.5), `Expected endpoint hover hit box to keep the original 1x size, got default=${JSON.stringify(defaultSource)} hover=${JSON.stringify(endpointHoverSource)}`)
  assert(closeToRatio(endpointHoverSource.dotScale, 3), `Expected endpoint hover dot scale 3x, got ${JSON.stringify(endpointHoverSource)}`)
  await maybeScreenshot(page, 'endpoint-hover')

  const screenHitRadius = (Number.parseFloat(defaultSource.hitWidth || '0') * defaultSource.paneScale) / 2
  await page.mouse.move(defaultSource.centerX + screenHitRadius - 1, defaultSource.centerY)
  await page.waitForTimeout(160)
  const radiusHoverSource = await portBox(page, sourceSelector)
  assert(
    closeToRatio(radiusHoverSource.dotScale, 3),
    `Expected endpoint hover radius to trigger 3x scale inside the 3x original diameter, got ${JSON.stringify(radiusHoverSource)}`,
  )
  await maybeScreenshot(page, 'endpoint-radius-hover')

  await page.mouse.move(defaultSource.centerX - screenHitRadius - 6, defaultSource.centerY)
  await page.waitForTimeout(160)
  const outsideRadiusSource = await portBox(page, sourceSelector)
  assert(
    closeToRatio(outsideRadiusSource.dotScale, 2),
    `Expected endpoint hover to fall back to node-hover 2x outside the 3x original diameter, got ${JSON.stringify(outsideRadiusSource)}`,
  )

  await node.click()
  await page.mouse.move(40, 40)
  await page.waitForTimeout(160)
  const selectedSource = await portBox(page, sourceSelector)
  assert(closeToRatio(selectedSource.dotScale, 1.2), `Expected selected node port dot scale 1.2x, got ${JSON.stringify(selectedSource)}`)
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
