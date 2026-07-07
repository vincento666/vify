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
  runId: 701,
  ownerType: 'WORKFLOW',
  ownerId: 12,
  ownerName: 'Workflow DAG Demo',
  status: 'RUNNING',
  state: 'running',
  tenantId: 'tenant-dag',
  queueState: 'running',
  createdAt: '2026-07-04T01:00:00Z',
  updatedAt: '2026-07-04T01:01:00Z',
}

const nodes = [
  { nodeKey: 'router', nodeType: 'CONDITION', name: 'Router', status: 'SUCCEEDED', selectionState: { state: 'completed' } },
  {
    nodeKey: 'vip',
    nodeType: 'MESSAGE',
    name: 'VIP Reply',
    status: 'SUCCEEDED',
    selectionState: { state: 'completed', selectedUpstreamNodeKeys: ['router'] },
  },
  {
    nodeKey: 'fallback',
    nodeType: 'MESSAGE',
    name: 'Fallback',
    status: 'SKIPPED',
    selectionState: { state: 'skipped', skippedUpstreamNodeKeys: ['router'] },
  },
  { nodeKey: 'llm', nodeType: 'LLM', name: 'LLM Draft', status: 'RUNNING', selectionState: { state: 'running' } },
  { nodeKey: 'question', nodeType: 'QUESTION', name: 'Collect Input', status: 'WAITING', selectionState: { state: 'waiting' } },
  { nodeKey: 'api', nodeType: 'API_CALL', name: 'API Failure', status: 'FAILED', selectionState: { state: 'failed' }, error: 'timeout' },
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
  await page.route('**/api/v1/runtime-runs/701', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: run }) })
  })
  await page.route('**/api/v1/runtime-runs/701/nodes', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: { list: nodes, total: nodes.length } }) })
  })

  await page.goto(withHostContext('/runtime-ops', { permissions: ['runtime_ops:read'] }), { waitUntil: 'networkidle' })
  await page.getByText('Workflow DAG Demo').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('runtime-ops-run-row').first().click()
  await page.getByTestId('runtime-ops-dag-view').waitFor({ state: 'visible', timeout: 10000 })

  for (const [nodeKey, label] of [
    ['vip', '已完成'],
    ['fallback', '已跳过'],
    ['llm', '运行中'],
    ['question', '等待中'],
    ['api', '已失败'],
  ]) {
    const card = page.getByTestId(`runtime-ops-dag-node-${nodeKey}`)
    await card.waitFor({ state: 'visible', timeout: 10000 })
    assert((await card.textContent()).includes(label), `Expected ${nodeKey} card to show ${label}`)
  }
  await page.getByText('selected router → vip').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText('skipped router → fallback').waitFor({ state: 'visible', timeout: 10000 })

  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })

  console.log('PASS runtime ops DAG view states')
} finally {
  await browser.close()
}
