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
      name: `021.6 Observe Redirect ${stamp}`,
      description: 'observe compatibility redirect e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'end',
          type: 'END',
          name: '结束',
          config: {
            outputVariable: 'final',
            output: 'observe redirect complete',
            ui: { position: { x: 520, y: 180 } },
          },
        },
      ],
      edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
    },
  }), 'create workflow')

  const run = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
    data: { input: { message: '兼容路由应该回到画布调试面板' } },
  }), 'run workflow')

  await page.goto(`${baseUrl}/observe?runId=${run.runId}`, { waitUntil: 'networkidle' })
  await page.waitForURL(`${baseUrl}/workflows/${workflow.id}/canvas?runId=${run.runId}&debug=1`, { timeout: 10000 })
  assert(!page.url().includes('/observe'), `Expected observe route to redirect, got ${page.url()}`)

  const dock = page.getByTestId('workflow-debug-dock')
  await dock.getByText(`Run #${run.runId}`, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  const dockText = await dock.textContent()
  assert(dockText.includes('observe redirect complete'), 'Expected embedded debug dock to show run output')
  assert(await page.getByTestId('observe-run-detail').count() === 0, 'Standalone observe detail should not render')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS observe compat redirect e2e workflow=${workflow.id} run=${run.runId}`)
} finally {
  await browser.close()
}
