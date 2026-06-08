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

async function canvasMetrics(page, nodeSelector) {
  return page.evaluate((selector) => {
    const flow = document.querySelector('.coze-flow')
    const viewport = document.querySelector('.vue-flow__viewport')
    const node = document.querySelector(selector)
    if (!flow || !viewport || !node) {
      throw new Error('Expected workflow canvas, viewport, and target node to be visible')
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
  }, nodeSelector)
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
          {
            nodeKey: 'variable_aggregation_1',
            type: 'VARIABLE_AGGREGATION',
            name: '变量聚合',
            config: {
              strategy: 'first_non_empty',
              groups: [
                {
                  name: 'selected',
                  type: 'string',
                  variables: [
                    { value: '{{start.input}}', type: 'string' },
                    { value: '{{llm_1.answer}}', type: 'string' },
                  ],
                },
              ],
              outputParameters: [{ name: 'selected', type: 'string' }],
              ui: { position: { x: 520, y: 420 } },
            },
          },
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
  async function assertNodeStable(nodeSelector, label) {
    await page.locator(nodeSelector).waitFor({ state: 'visible', timeout: 10000 })
    const beforeOpen = await canvasMetrics(page, nodeSelector)

    await page.locator(nodeSelector).click()
    const panel = page.locator('[data-testid="node-config-panel"]')
    await panel.waitFor({ state: 'visible', timeout: 5000 })
    await page.waitForTimeout(260)
    const afterOpen = await canvasMetrics(page, nodeSelector)
    assertStableMetrics(beforeOpen, afterOpen, `opening ${label} config panel`)

    await panel.getByRole('button', { name: '关闭配置' }).click()
    await panel.waitFor({ state: 'hidden', timeout: 5000 })
    await page.waitForTimeout(260)
    const afterClose = await canvasMetrics(page, nodeSelector)
    assertStableMetrics(beforeOpen, afterClose, `closing ${label} config panel`)
  }

  await assertNodeStable('.coze-node.node-llm', 'LLM')
  await assertNodeStable('.coze-node.node-variable_aggregation', 'variable aggregation')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow config panel zoom stability e2e')
} finally {
  await browser.close()
}
