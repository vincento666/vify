import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  if (!response.ok()) {
    const text = await response.text()
    throw new Error(`${label} HTTP ${response.status()} ${text}`)
  }
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

function humanInputChatflow(name) {
  return {
    name,
    description: 'runtime v2 cancel debug control browser UAT',
    nodes: [
      { nodeKey: 'start', type: 'START', name: 'Start', config: { ui: { position: { x: 120, y: 180 } } } },
      {
        nodeKey: 'human_input_1',
        type: 'HUMAN_INPUT',
        name: 'Human Review',
        config: {
          prompt: 'Please review before continuing.',
          outputVariable: 'payload',
          ui: { position: { x: 460, y: 180 } },
        },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: 'End',
        config: {
          outputVariable: 'final',
          output: 'approved={{human_input_1.approved}} note={{human_input_1.note}}',
          ui: { position: { x: 820, y: 180 } },
        },
      },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'human_input_1', condition: null },
      { sourceNodeKey: 'human_input_1', targetNodeKey: 'end', condition: null },
    ],
  }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  const stamp = Date.now()
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: humanInputChatflow(`104 Runtime V2 Cancel UI ${stamp}`),
    }),
    'create chatflow',
  )

  const cancelRequests = []
  page.on('request', (request) => {
    if (request.method() === 'POST' && request.url().includes('/api/v1/runtime-runs/') && request.url().endsWith('/cancel')) {
      cancelRequests.push(request.url())
    }
  })

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByTestId('canvas-bottom-toolbar').getByRole('button', { name: '试运行', exact: true }).click()
  const panel = page.getByTestId('test-run-panel')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByTestId('chatflow-run-message-input').fill('Please start the human review path')
  await panel.getByRole('button', { name: '发送消息', exact: true }).click()
  await panel.getByText('INTERRUPTED', { exact: true }).waitFor({ state: 'visible', timeout: 12000 })
  const panelText = await panel.textContent()
  const panelRunId = panelText?.match(/Run #(\d+)/)?.[1]
  assert(panelRunId, `Expected runtime v2 run id in panel: ${panelText}`)

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas?debug=1&runId=${panelRunId}&runtime=v2`, { waitUntil: 'networkidle' })
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.waitFor({ state: 'visible', timeout: 10000 })
  await dock.getByText(/当前运行 #\d+ · INTERRUPTED/).waitFor({ state: 'visible', timeout: 12000 })
  const cancelButton = dock.getByTestId('debug-runtime-v2-cancel')
  await cancelButton.waitFor({ state: 'visible', timeout: 10000 })
  await cancelButton.click()

  await dock.getByText(/当前运行 #\d+ · CANCELLED/).waitFor({ state: 'visible', timeout: 12000 })
  assert(cancelRequests.length === 1, `Expected one cancel request, got ${cancelRequests.length}`)

  const titleText = await dock.locator('.debug-dock-title').textContent()
  const runIdMatch = titleText?.match(/#(\d+)/)
  assert(runIdMatch, `Expected run id in debug title: ${titleText}`)
  const runId = Number(runIdMatch[1])
  const terminal = await unwrap(await page.request.get(`${baseUrl}/api/v1/runtime-runs/${runId}/result`), 'get cancelled result')
  assert(terminal.status === 'CANCELLED', `Expected durable CANCELLED, got ${terminal.status}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS runtime v2 cancel debug control chatflow=${chatflow.id} run=${runId}`)
} finally {
  await browser.close()
}
