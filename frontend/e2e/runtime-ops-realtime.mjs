import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const streamCursors = []

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function withHostContext(path, context) {
  return `${baseUrl}${path}?hifyHostContext=${encodeURIComponent(JSON.stringify(context))}`
}

function sseFrame(event) {
  return `data: ${JSON.stringify(event)}\n\n`
}

const run = {
  runId: 990,
  ownerType: 'WORKFLOW',
  ownerId: 12,
  ownerName: 'Runtime Realtime Demo',
  status: 'RUNNING',
  state: 'running',
  tenantId: 'tenant-realtime',
  queueState: 'running',
  createdAt: '2026-07-04T03:00:00Z',
  updatedAt: '2026-07-04T03:01:00Z',
}

const nodes = [
  {
    id: 1,
    nodeKey: 'llm_1',
    nodeType: 'LLM',
    name: 'Realtime LLM',
    status: 'RUNNING',
    selectionState: { state: 'running' },
  },
]

const events = [
  {
    id: 1,
    runId: 990,
    sequence: 1,
    type: 'workflow_node_started',
    nodeId: 'llm_1',
    payload: { status: 'RUNNING' },
    createdAt: '2026-07-04T03:00:01Z',
  },
  {
    id: 2,
    runId: 990,
    sequence: 2,
    type: 'workflow_node_completed',
    nodeId: 'llm_1',
    payload: { status: 'COMPLETED', output: { answer: 'stream recovered' } },
    createdAt: '2026-07-04T03:00:02Z',
  },
]

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.route(/\/api\/v1\/runtime-runs(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: 'OK', data: { list: [run], total: 1, page: 1, pageSize: 20 } }),
    })
  })
  await page.route('**/api/v1/runtime-runs/990', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: run }) })
  })
  await page.route('**/api/v1/runtime-runs/990/nodes', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: { list: nodes, total: nodes.length } }) })
  })
  await page.route('**/api/v1/runtime-runs/990/events/stream**', async (route) => {
    const url = new URL(route.request().url())
    const afterSequence = Number(url.searchParams.get('afterSequence') || 0)
    streamCursors.push(afterSequence)
    const event = afterSequence === 0 ? events[0] : events[1]
    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      body: sseFrame(event),
    })
  })
  await page.route(/\/api\/v1\/runtime-runs\/990\/events(?:\?.*)?$/, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: { list: [], total: 0 } }) })
  })
  await page.route('**/api/v1/runtime-jobs/dlq**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: 'OK', data: { list: [], total: 0, page: 1, pageSize: 20 } }),
    })
  })
  await page.route(/\/api\/v1\/runtime-jobs(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: 'OK', data: { list: [], total: 0, page: 1, pageSize: 20 } }),
    })
  })

  await page.goto(withHostContext('/runtime-ops', { permissions: ['runtime_ops:read'] }), { waitUntil: 'networkidle' })
  await page.getByText('Runtime Realtime Demo').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('runtime-ops-run-row').first().click()
  const status = page.getByTestId('runtime-ops-realtime-status')
  await status.waitFor({ state: 'visible', timeout: 10000 })
  const deadline = Date.now() + 10000
  let statusText = ''
  while (Date.now() < deadline) {
    statusText = await status.textContent()
    if (statusText.includes('seq 2') && streamCursors[0] === 0 && streamCursors[1] === 1) break
    await page.waitForTimeout(50)
  }
  statusText = await status.textContent()
  assert(statusText.includes('workflow_node_completed'), `Expected latest realtime event type: ${statusText}`)
  assert(streamCursors[0] === 0, `Expected first stream cursor 0, got ${streamCursors.join(',')}`)
  assert(streamCursors[1] === 1, `Expected reconnect cursor 1, got ${streamCursors.join(',')}`)

  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })

  console.log('PASS runtime ops realtime SSE reconnect')
} finally {
  await browser.close()
}
