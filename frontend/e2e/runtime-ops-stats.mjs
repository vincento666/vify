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
  runId: 880,
  ownerType: 'WORKFLOW',
  ownerId: 12,
  ownerName: 'Runtime Stats Demo',
  status: 'FAILED',
  state: 'failed',
  tenantId: 'tenant-stats',
  queueState: 'completed',
  createdAt: '2026-07-04T02:00:00Z',
  updatedAt: '2026-07-04T02:01:00Z',
}

const nodes = [
  { id: 1, nodeKey: 'llm_1', nodeType: 'LLM', name: 'LLM Provider', status: 'FAILED', selectionState: { state: 'failed' } },
  { id: 2, nodeKey: 'api_1', nodeType: 'API_CALL', name: 'Order API', status: 'COMPLETED', selectionState: { state: 'completed' } },
  { id: 3, nodeKey: 'tool_1', nodeType: 'TOOL_CALL', name: 'Lookup Tool', status: 'COMPLETED', selectionState: { state: 'completed' } },
]

const events = [
  {
    id: 1,
    runId: 880,
    sequence: 1,
    type: 'workflow_node_external_call_failed',
    nodeId: 'llm_1',
    payload: {
      callType: 'LLM',
      providerKey: 'llm:gpt-4o',
      errorKind: 'provider_timeout',
      message: 'provider timeout',
      attempts: 3,
      retryCount: 2,
      breakerOpen: true,
    },
    createdAt: '2026-07-04T02:00:01Z',
  },
  {
    id: 2,
    runId: 880,
    sequence: 2,
    type: 'workflow_node_external_call_failed',
    nodeId: 'api_1',
    payload: {
      callType: 'API_CALL',
      providerKey: 'api:orders',
      errorKind: 'provider_error',
      message: 'orders 500',
      attempts: 2,
      retryCount: 1,
    },
    createdAt: '2026-07-04T02:00:02Z',
  },
  {
    id: 3,
    runId: 880,
    sequence: 3,
    type: 'workflow_node_completed',
    nodeId: 'tool_1',
    payload: { callType: 'TOOL_CALL', providerKey: 'tool:lookup_order' },
    createdAt: '2026-07-04T02:00:03Z',
  },
]

const jobs = [
  {
    jobId: 990,
    runId: 880,
    ownerType: 'WORKFLOW',
    ownerId: 12,
    status: 'QUEUED',
    attemptCount: 2,
    maxAttempts: 5,
    nextRetryAt: '2026-07-04T02:05:00Z',
    lastError: 'provider timeout',
    tenantId: 'tenant-stats',
  },
]

const dlq = [
  {
    jobId: 991,
    runId: 880,
    ownerType: 'WORKFLOW',
    ownerId: 12,
    status: 'FAILED',
    attemptCount: 5,
    maxAttempts: 5,
    lastError: 'tool exhausted',
    updatedAt: '2026-07-04T02:06:00Z',
    tenantId: 'tenant-stats',
  },
]

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.route('**/api/v1/runtime-jobs/dlq**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: 'OK', data: { list: dlq, total: dlq.length, page: 1, pageSize: 20 } }),
    })
  })
  await page.route(/\/api\/v1\/runtime-jobs(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: 'OK', data: { list: jobs, total: jobs.length, page: 1, pageSize: 20 } }),
    })
  })
  await page.route(/\/api\/v1\/runtime-runs(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: 'OK', data: { list: [run], total: 1, page: 1, pageSize: 20 } }),
    })
  })
  await page.route('**/api/v1/runtime-runs/880', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: run }) })
  })
  await page.route('**/api/v1/runtime-runs/880/nodes', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: { list: nodes, total: nodes.length } }) })
  })
  await page.route('**/api/v1/runtime-runs/880/events**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: { list: events, total: events.length } }) })
  })

  await page.goto(withHostContext('/runtime-ops', { permissions: ['runtime_ops:read'] }), { waitUntil: 'networkidle' })
  await page.getByText('Runtime Stats Demo').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('runtime-ops-run-row').first().click()
  await page.getByRole('tab', { name: 'Stats' }).click()
  const stats = page.getByTestId('runtime-ops-stats')
  await stats.waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText('Job #990').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText('DLQ #991').waitFor({ state: 'visible', timeout: 10000 })
  const text = await stats.textContent()

  assert(text.includes('Provider'), 'Expected provider stats')
  assert(text.includes('API'), 'Expected API stats')
  assert(text.includes('Tool'), 'Expected tool stats')
  assert(text.includes('llm:gpt-4o'), 'Expected provider failure row')
  assert(text.includes('api:orders'), 'Expected API failure row')
  assert(text.includes('Job #990'), 'Expected retry job row')
  assert(text.includes('DLQ #991'), 'Expected DLQ failure row')
  assert(text.includes('breaker open'), 'Expected breaker state evidence')

  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })

  console.log('PASS runtime ops stats failure and retry panel')
} finally {
  await browser.close()
}
