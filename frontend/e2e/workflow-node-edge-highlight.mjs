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

async function strokeWidth(page, index = 0) {
  const path = page.locator('.vue-flow__edge-path').nth(index)
  return Number.parseFloat(await path.evaluate((element) => getComputedStyle(element).strokeWidth))
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name: `Node Edge Highlight ${Date.now()}`,
        description: 'node hover and selection edge affordance e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['input'], ui: { position: { x: 160, y: 240 } } } },
          {
            nodeKey: 'llm_1',
            type: 'LLM',
            name: '大模型',
            config: {
              inputParameters: [{ name: 'input', type: 'string', value: '{{start.input}}' }],
              outputParameters: [{ name: 'output', type: 'string' }],
              ui: { position: { x: 560, y: 220 } },
            },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{llm_1.output}}', ui: { position: { x: 980, y: 240 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create node edge highlight workflow',
  )

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__edge').first().waitFor({ state: 'visible', timeout: 5000 })

  const defaultStrokeWidth = await strokeWidth(page)
  const llmNode = page.locator('.vue-flow__node[data-id="llm_1"] .coze-node')
  await llmNode.hover()
  await page.waitForTimeout(180)
  assert(await page.locator('.coze-edge-path.edge-hovered').count() === 2, 'Hovering a node should highlight all connected edges')
  assert(await page.locator('.coze-edge-path.edge-selected').count() === 0, 'Node hover should not select connected edges')
  const hoveredStrokeWidth = await strokeWidth(page)
  assert(
    Math.abs(hoveredStrokeWidth - defaultStrokeWidth) <= Math.max(0.15, defaultStrokeWidth * 0.05),
    `Node hover should keep hover edge width ${defaultStrokeWidth}, got ${hoveredStrokeWidth}`,
  )

  await page.mouse.move(80, 820)
  await page.waitForTimeout(180)
  assert(await page.locator('.coze-edge-path.edge-hovered').count() === 0, 'Leaving a node should clear connected edge hover state')

  await llmNode.click()
  await page.waitForTimeout(180)
  assert(await page.locator('.coze-edge-path.edge-selected').count() === 2, 'Selecting a node should give all connected edges selected styling')
  assert(await page.locator('.coze-edge-path.edge-hovered').count() === 0, 'Selected node edges should not also keep hover styling')
  const selectedStrokeWidth = await strokeWidth(page)
  assert(
    Math.abs(selectedStrokeWidth - defaultStrokeWidth * 1.5) <= 0.15,
    `Selected node should apply selected edge width ${defaultStrokeWidth * 1.5}, got ${selectedStrokeWidth}`,
  )

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  await page.locator('.vue-flow__pane').click({ position: { x: 32, y: 32 }, force: true })
  await page.waitForTimeout(180)
  assert(await page.locator('.coze-edge-path.edge-selected').count() === 0, 'Pane click should clear node-selected edge styling')

  console.log(`PASS workflow node edge highlight e2e workflow=${workflow.id}`)
} finally {
  await browser.close()
}
