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

async function canvasMetrics(page) {
  return page.evaluate(() => {
    const flow = document.querySelector('.coze-flow')
    const viewport = document.querySelector('.vue-flow__viewport')
    const node = document.querySelector('.coze-node.node-llm')
    if (!flow || !viewport || !node) {
      throw new Error('Expected workflow canvas, viewport, and LLM node to be visible')
    }
    const flowRect = flow.getBoundingClientRect()
    const nodeRect = node.getBoundingClientRect()
    const transform = window.getComputedStyle(viewport).transform
    const match = transform.match(/matrix\(([^,]+),/)
    return {
      flowWidth: flowRect.width,
      nodeWidth: nodeRect.width,
      viewportScale: match ? Number(match[1]) : 1,
    }
  })
}

function assertStableMetrics(before, after, label) {
  assert(
    Math.abs(before.flowWidth - after.flowWidth) <= 1,
    `${label}: flow width changed from ${before.flowWidth} to ${after.flowWidth}`,
  )
  assert(
    Math.abs(before.nodeWidth - after.nodeWidth) <= 1,
    `${label}: node width changed from ${before.nodeWidth} to ${after.nodeWidth}`,
  )
  assert(
    Math.abs(before.viewportScale - after.viewportScale) <= 0.01,
    `${label}: viewport scale changed from ${before.viewportScale} to ${after.viewportScale}`,
  )
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name: `Config Zoom Stability ${Date.now()}`,
        description: 'opening config panel must not resize or refit the canvas',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['input'], ui: { position: { x: 160, y: 180 } } } },
          { nodeKey: 'llm_1', type: 'LLM', name: '大模型', config: { inputParameters: [{ name: 'input', value: '{{start.input}}' }], outputVariable: 'answer', ui: { position: { x: 520, y: 180 } } } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { output: '{{llm_1.answer}}', ui: { position: { x: 920, y: 180 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create workflow',
  )

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-llm').waitFor({ state: 'visible', timeout: 10000 })
  const beforeOpen = await canvasMetrics(page)

  await page.locator('.coze-node.node-llm').click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await page.waitForTimeout(260)
  const afterOpen = await canvasMetrics(page)
  assertStableMetrics(beforeOpen, afterOpen, 'opening config panel')

  await panel.getByRole('button', { name: '关闭配置' }).click()
  await panel.waitFor({ state: 'hidden', timeout: 5000 })
  await page.waitForTimeout(260)
  const afterClose = await canvasMetrics(page)
  assertStableMetrics(beforeOpen, afterClose, 'closing config panel')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow config panel zoom stability e2e')
} finally {
  await browser.close()
}
