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

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `015.3 Intent Chatflow ${Date.now()}`,
        description: 'intent recognition e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 120, y: 160 } } } },
          {
            nodeKey: 'intent_1',
            type: 'INTENT_RECOGNITION',
            name: '意图识别',
            config: {
              inputSource: '{{start.sys.query}}',
              outputVariable: 'intent',
              defaultIntent: 'default',
              classifierMode: 'fake',
              intents: [
                { key: 'refund', name: '退款', description: '用户要退款或售后', examples: ['退款', '退货', '售后'] },
                { key: 'shipping', name: '物流', description: '用户查询物流、快递或配送', examples: ['物流', '快递', '配送'] },
              ],
              ui: { position: { x: 480, y: 160 } },
            },
          },
          { nodeKey: 'refund_end', type: 'END', name: '退款路径', config: { outputVariable: 'final', output: 'refund path', ui: { position: { x: 840, y: 60 } } } },
          { nodeKey: 'shipping_end', type: 'END', name: '物流路径', config: { outputVariable: 'final', output: 'shipping path', ui: { position: { x: 840, y: 220 } } } },
          { nodeKey: 'default_end', type: 'END', name: '默认路径', config: { outputVariable: 'final', output: 'default path', ui: { position: { x: 840, y: 380 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'intent_1', condition: null },
          { sourceNodeKey: 'intent_1', targetNodeKey: 'refund_end', condition: 'refund' },
          { sourceNodeKey: 'intent_1', targetNodeKey: 'shipping_end', condition: 'shipping' },
          { sourceNodeKey: 'intent_1', targetNodeKey: 'default_end', condition: null },
        ],
      },
    }),
    'create intent chatflow',
  )

  const refundRun = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
      data: { input: { 'sys.query': '我要退款，订单有问题' } },
    }),
    'run refund intent',
  )
  assert(refundRun.output.final === 'refund path', `Expected refund branch, got ${JSON.stringify(refundRun.output)}`)

  const shippingNodeRun = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/nodes/intent_1/runs`, {
      data: { input: { 'sys.query': '查物流' } },
    }),
    'selected intent node run',
  )
  assert(shippingNodeRun.output.intent === 'shipping', `Expected shipping intent, got ${JSON.stringify(shippingNodeRun.output)}`)
  assert(String(shippingNodeRun.output.reason).includes('matched'), 'Expected selected node run reason')

  const defaultRun = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
      data: { input: { 'sys.query': '今天北京天气' } },
    }),
    'run default intent',
  )
  assert(defaultRun.output.final === 'default path', `Expected default branch, got ${JSON.stringify(defaultRun.output)}`)

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-intent_recognition').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.coze-node.node-intent_recognition').click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const panelText = await panel.innerText()
  assert(panelText.includes('识别策略'), 'Expected classifier strategy section')
  assert(panelText.includes('意图分支'), 'Expected intent branch section')
  assert(panelText.includes('输入来源'), 'Expected input source field')
  await panel.locator('[data-testid="intent-row-editor"]').waitFor({ state: 'visible', timeout: 5000 })
  assert(await panel.locator('[data-testid="intent-row"]').count() >= 2, 'Expected structured intent rows')
  assert(panelText.includes('默认意图'), 'Expected default intent field')
  assert(panelText.includes('分类模式'), 'Expected classifier mode field')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow intent recognition e2e')
} finally {
  await browser.close()
}
