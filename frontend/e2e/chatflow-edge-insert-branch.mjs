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
  const chatflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `025.7 Branch Edge Insert ${Date.now()}`,
      description: 'branch edge insert e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 120, y: 260 } } } },
        { nodeKey: 'intent_1', type: 'INTENT_RECOGNITION', name: '意图识别', config: { outputVariable: 'intent', ui: { position: { x: 480, y: 260 } } } },
        { nodeKey: 'refund_end', type: 'END', name: '退款结束', config: { outputVariable: 'output', output: 'refund', ui: { position: { x: 860, y: 160 } } } },
        { nodeKey: 'default_end', type: 'END', name: '默认结束', config: { outputVariable: 'output', output: 'default', ui: { position: { x: 860, y: 360 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'intent_1', condition: null },
        { sourceNodeKey: 'intent_1', targetNodeKey: 'refund_end', condition: 'refund' },
        { sourceNodeKey: 'intent_1', targetNodeKey: 'default_end', condition: null },
      ],
    },
  }), 'create branch insert chatflow')

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  const branchEdge = page.locator('.vue-flow__edge[data-id="intent_1->refund_end"]')
  await branchEdge.waitFor({ state: 'visible', timeout: 5000 })
  await branchEdge.locator('.vue-flow__edge-interaction').hover({ force: true })
  const insertButton = page.getByTestId('edge-insert-button').filter({ visible: true })
  assert(await insertButton.count() === 1, 'Expected one visible edge insert button')
  await insertButton.click()
  const palette = page.getByTestId('edge-insert-palette')
  await palette.waitFor({ state: 'visible', timeout: 5000 })
  await palette.getByRole('button', { name: '大模型', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="llm_1"]').waitFor({ state: 'visible', timeout: 5000 })
  await page.getByTestId('node-config-panel').waitFor({ state: 'visible', timeout: 5000 })
  assert(await page.getByTestId('node-config-panel').getByText('大模型', { exact: true }).count() >= 1, 'Expected inserted node config panel to open')
  assert(await page.getByTestId('edge-insert-palette').count() === 0, 'Expected palette to close after insertion')

  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForTimeout(500)
  const saved = await unwrap(await page.request.get(`${baseUrl}/api/v1/chatflows/${chatflow.id}`), 'reload saved chatflow')
  const edges = saved.edges || []
  assert(edges.some((edge) => edge.sourceNodeKey === 'intent_1' && edge.targetNodeKey === 'llm_1' && edge.condition === 'refund'), `Expected upstream branch condition to be preserved: ${JSON.stringify(edges)}`)
  assert(edges.some((edge) => edge.sourceNodeKey === 'llm_1' && edge.targetNodeKey === 'refund_end' && edge.condition === null), `Expected inserted node to reconnect to original target: ${JSON.stringify(edges)}`)
  assert(!edges.some((edge) => edge.sourceNodeKey === 'intent_1' && edge.targetNodeKey === 'refund_end'), `Expected original edge to be removed: ${JSON.stringify(edges)}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS 025.7 branch edge insert e2e chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
