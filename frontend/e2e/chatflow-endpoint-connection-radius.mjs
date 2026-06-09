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

async function portMetrics(page, selector) {
  return page.evaluate((portSelector) => {
    const element = document.querySelector(portSelector)
    if (!element) return null
    const box = element.getBoundingClientRect()
    const matrixScale = (value) => {
      const matrix = String(value || '').match(/matrix\(([^,]+)/)
      return matrix ? Number.parseFloat(matrix[1]) : 1
    }
    const dotStyle = getComputedStyle(element, '::after')
    const className = element.getAttribute('class') || ''
    return {
      width: box.width,
      height: box.height,
      centerX: box.left + box.width / 2,
      centerY: box.top + box.height / 2,
      dotScale: matrixScale(dotStyle.transform),
      className,
    }
  }, selector)
}

function closeToRatio(actual, expected, tolerance = 0.14) {
  return Math.abs(actual - expected) <= tolerance
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const chatflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `Endpoint Connection Radius ${Date.now()}`,
      description: 'endpoint connection radius e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 220 } } } },
        { nodeKey: 'llm_1', type: 'LLM', name: '大模型', config: { outputVariable: 'answer', ui: { position: { x: 560, y: 220 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{llm_1.answer}}', ui: { position: { x: 980, y: 220 } } } },
      ],
      edges: [],
    },
  }), 'create endpoint connection radius chatflow')

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })

  const sourceSelector = '.vue-flow__node[data-id="start"] .source-port'
  const targetSelector = '.vue-flow__node[data-id="llm_1"] .target-port'
  const source = await portMetrics(page, sourceSelector)
  const target = await portMetrics(page, targetSelector)
  assert(source && target, 'Expected source and target ports to render')

  await page.mouse.move(source.centerX, source.centerY)
  await page.mouse.down()
  const magneticEdgeDistance = Math.max(4, target.width / 2 - 1)
  await page.mouse.move(target.centerX - magneticEdgeDistance, target.centerY, { steps: 18 })
  await page.waitForTimeout(180)

  const nearTarget = await portMetrics(page, targetSelector)
  assert(nearTarget, 'Expected target port after connection drag')
  assert(
    closeToRatio(nearTarget.dotScale, 1.2),
    `Expected target endpoint dot to scale to 1.2x inside the original-hitbox hover radius, distance=${magneticEdgeDistance}, got metrics=${JSON.stringify(nearTarget)}`,
  )

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  await page.mouse.up()

  console.log(`PASS chatflow endpoint connection radius e2e chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
