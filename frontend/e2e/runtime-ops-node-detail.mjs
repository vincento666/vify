import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function withHostContext(path, context) {
  return `${baseUrl}${path}?hifyHostContext=${encodeURIComponent(JSON.stringify(context))}`
}

const run = {
  runId: 801,
  ownerType: 'WORKFLOW',
  ownerId: 12,
  ownerName: 'Workflow Node Detail Demo',
  status: 'FAILED',
  state: 'failed',
  tenantId: 'tenant-node-detail',
  queueState: 'completed',
  createdAt: '2026-07-04T01:00:00Z',
  updatedAt: '2026-07-04T01:01:00Z',
}

const nodes = [
  {
    id: 901,
    nodeKey: 'llm_1',
    nodeType: 'LLM',
    name: 'LLM Draft',
    status: 'FAILED',
    elapsedMs: 1234,
    inputs: { query: 'refund policy', reasoning: 'secret chain of thought input' },
    outputs: {
      answer: 'Refund within 7 days',
      toolCalls: [{ name: 'lookup_policy', status: 'failed' }],
      thought: 'secret chain of thought output',
      __debug: { llm: { reasoning: 'hidden provider reasoning' } },
    },
    error: 'provider timeout',
    selectionState: { state: 'failed' },
  },
]

const events = [
  {
    id: 1,
    runId: 801,
    sequence: 1,
    type: 'workflow_node_started',
    nodeId: 'llm_1',
    payload: { status: 'RUNNING' },
    createdAt: '2026-07-04T01:00:00Z',
  },
  {
    id: 2,
    runId: 801,
    sequence: 2,
    type: 'workflow_node_external_call_failed',
    nodeId: 'llm_1',
    payload: { callType: 'LLM', error: 'provider timeout', retryable: true },
    createdAt: '2026-07-04T01:00:01Z',
  },
  {
    id: 3,
    runId: 801,
    sequence: 3,
    type: 'workflow_node_failed',
    nodeId: 'llm_1',
    payload: { error: 'provider timeout' },
    createdAt: '2026-07-04T01:00:02Z',
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
  await page.route('**/api/v1/runtime-runs/801', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: run }) })
  })
  await page.route('**/api/v1/runtime-runs/801/nodes', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: { list: nodes, total: nodes.length } }) })
  })
  await page.route('**/api/v1/runtime-runs/801/events**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: { list: events, total: events.length } }) })
  })

  await page.goto(withHostContext('/runtime-ops', { permissions: ['runtime_ops:read'] }), { waitUntil: 'networkidle' })
  await page.getByText('Workflow Node Detail Demo').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('runtime-ops-run-row').first().click()
  await page.getByTestId('runtime-ops-dag-node-llm_1').click()
  const detail = page.getByTestId('runtime-ops-node-detail')
  await detail.waitFor({ state: 'visible', timeout: 10000 })

  const text = await detail.textContent()
  assert(text.includes('LLM Draft'), 'Expected node name')
  assert(text.includes('1234ms'), 'Expected duration')
  assert(text.includes('provider timeout'), 'Expected error evidence')
  assert(text.includes('Refund within 7 days'), 'Expected output summary')
  assert(text.includes('workflow_node_external_call_failed'), 'Expected event timeline')
  assert(!text.includes('secret chain'), 'Reasoning must be hidden by default')
  assert(!text.includes('hidden provider reasoning'), 'Provider reasoning must be hidden by default')

  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })

  console.log('PASS runtime ops node detail timeline')
} finally {
  await browser.close()
}
