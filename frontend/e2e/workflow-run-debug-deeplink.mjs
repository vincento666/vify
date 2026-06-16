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
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  const stamp = Date.now()
  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `021.2 Workflow Run Debug ${stamp}`,
      description: 'workflow embedded run debug deeplink e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 140, y: 180 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'answer', output: 'debug {{start.USER_INPUT}}', ui: { position: { x: 620, y: 180 } } } },
      ],
      edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
    },
  }), 'create workflow')

  const run = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
    data: { input: { USER_INPUT: 'deep link payload' } },
  }), 'run workflow')

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas?runId=${run.runId}&debug=1`, { waitUntil: 'networkidle' })
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.waitFor({ state: 'visible', timeout: 10000 })
  const dockText = await dock.innerText()
  assert(page.url().includes(`/workflows/${workflow.id}/canvas`), `Expected to stay in workflow canvas, got ${page.url()}`)
  assert(!page.url().includes('/observe'), `Expected no observe navigation, got ${page.url()}`)
  assert(dockText.includes(`Run #${run.runId}`), `Expected selected run id in dock, got ${dockText}`)
  assert(dockText.includes('SUCCEEDED'), 'Expected successful run status in dock')
  assert(dockText.includes('调用树'), 'Expected call tree section in dock')
  assert(dockText.includes('火焰图'), 'Expected flamegraph section in dock')
  const callTreeText = await dock.getByTestId('workflow-run-call-tree').innerText()
  assert(!callTreeText.includes('start'), `Expected call tree to hide START node, got ${callTreeText}`)
  assert(!callTreeText.includes('end'), `Expected call tree to hide END node, got ${callTreeText}`)
  assert(await page.locator('.coze-node .node-run-status.status-succeeded').count() >= 2, 'Expected canvas node cards to show run status')
  assert(dockText.includes('deep link payload'), 'Expected node output payload in run detail')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS workflow run debug deeplink workflow=${workflow.id} run=${run.runId}`)
} finally {
  await browser.close()
}
