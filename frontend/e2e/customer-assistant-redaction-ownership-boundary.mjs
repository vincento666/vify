import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function hostHeaders(tenant, operator, permissions = 'customer_assistant:read,customer_assistant:operate') {
  return {
    'Content-Type': 'application/json',
    'X-Hify-Actor-Id': operator,
    'X-Hify-Actor-Name': operator,
    'X-Hify-Tenant-Id': tenant,
    'X-Hify-Org-Id': tenant,
    'X-Hify-Source': 'embedded-demo-shell',
    'X-Hify-Permissions': permissions,
    'X-Request-Id': `req-${tenant}-${operator}`,
  }
}

const ownerHeaders = hostHeaders('tenant-0782-a', 'operator-0782-a')
const otherHeaders = hostHeaders('tenant-0782-b', 'operator-0782-b')
const ownerReadHeaders = hostHeaders('tenant-0782-a', 'operator-0782-a', 'customer_assistant:read')
const otherReadHeaders = hostHeaders('tenant-0782-b', 'operator-0782-b', 'customer_assistant:read')

async function api(page, path, options = {}) {
  return page.evaluate(
    async ({ path, options }) => {
      const response = await fetch(`/api/v1${path}`, options)
      return {
        ok: response.ok,
        status: response.status,
        body: await response.json(),
      }
    },
    { path, options },
  )
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1200, height: 760 } })

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })

  const created = await api(page, '/customer-assistant/sessions', {
    method: 'POST',
    headers: ownerHeaders,
    body: JSON.stringify({ context: { customerId: 'C-0782-A' } }),
  })
  assert(created.ok, `Expected owner session create, got ${created.status}`)
  const sessionId = created.body.data.id

  const first = await api(page, `/customer-assistant/sessions/${sessionId}/turns`, {
    method: 'POST',
    headers: ownerHeaders,
    body: JSON.stringify({ message: '我要退票', idempotencyKey: 'uat-0782-start' }),
  })
  assert(first.ok, `Expected owner first turn, got ${first.status}`)
  const runId = first.body.data.runId
  const workerRunId = first.body.data.taskSummaries[0].workerAsyncRefs.workerRunId

  const sensitiveMessage = '订单号 TK-100 手机号 13800138000 乘机人 张三 邮箱 leak@example.com token=browser-token'
  const details = await api(page, `/customer-assistant/sessions/${sessionId}/turns`, {
    method: 'POST',
    headers: ownerHeaders,
    body: JSON.stringify({ message: sensitiveMessage, idempotencyKey: 'uat-0782-details' }),
  })
  assert(details.ok, `Expected owner details turn, got ${details.status}`)

  const completed = await api(page, `/customer-assistant/sessions/${sessionId}/turns`, {
    method: 'POST',
    headers: ownerHeaders,
    body: JSON.stringify({ message: '确认', idempotencyKey: 'uat-0782-confirm' }),
  })
  assert(completed.ok, `Expected owner completion turn, got ${completed.status}`)
  const action = completed.body.data.proposedActions[0] || details.body.data.proposedActions[0]
  assert(action, 'Expected refund proposed action after details and confirmation turns')
  const actionId = action.id

  const replay = await api(page, `/customer-assistant/sessions/${sessionId}/turns`, {
    method: 'POST',
    headers: ownerHeaders,
    body: JSON.stringify({ message: '确认', idempotencyKey: 'uat-0782-confirm' }),
  })
  assert(replay.ok && replay.body.data.replayed, `Expected redacted replay, got ${replay.status}`)

  await api(page, `/customer-assistant/proposed-actions/${actionId}/confirm`, {
    method: 'POST',
    headers: ownerHeaders,
  })
  const executed = await api(page, `/customer-assistant/proposed-actions/${actionId}/execute`, {
    method: 'POST',
    headers: ownerHeaders,
  })
  assert(executed.ok, `Expected execute action, got ${executed.status}`)

  const tasks = await api(page, `/customer-assistant/sessions/${sessionId}/tasks`, { headers: ownerReadHeaders })
  const events = await api(page, `/customer-assistant/sessions/${sessionId}/events`, { headers: ownerReadHeaders })
  const actions = await api(page, `/customer-assistant/sessions/${sessionId}/proposed-actions`, {
    headers: ownerReadHeaders,
  })
  const run = await api(page, `/customer-assistant/runs/${runId}`, { headers: ownerReadHeaders })
  const publicText = JSON.stringify({ replay: replay.body.data, tasks, events, actions, run })
  for (const raw of ['13800138000', 'TK-100', 'leak@example.com', 'browser-token']) {
    assert(!publicText.includes(raw), `Public response leaked ${raw}`)
  }
  assert(publicText.includes('[REDACTED]'), 'Expected redaction marker in public response')
  assert(publicText.includes('***'), 'Expected secret marker in public response')

  const denied = [
    await api(page, `/customer-assistant/sessions/${sessionId}/tasks`, { headers: otherReadHeaders }),
    await api(page, `/customer-assistant/sessions/${sessionId}/events`, { headers: otherReadHeaders }),
    await api(page, `/customer-assistant/sessions/${sessionId}/proposed-actions`, { headers: otherReadHeaders }),
    await api(page, `/customer-assistant/sessions/${sessionId}/metrics`, { headers: otherReadHeaders }),
    await api(page, `/customer-assistant/runs/${runId}`, { headers: otherReadHeaders }),
    await api(page, `/customer-assistant/worker-runs/${workerRunId}`, { headers: otherReadHeaders }),
    await api(page, `/customer-assistant/worker-runs/${workerRunId}/result`, { headers: otherReadHeaders }),
    await api(page, `/customer-assistant/worker-runs/${workerRunId}/events`, { headers: otherReadHeaders }),
    await api(page, `/customer-assistant/proposed-actions/${actionId}`, {
      method: 'PATCH',
      headers: otherHeaders,
      body: JSON.stringify({ title: 'wrong tenant' }),
    }),
  ]
  for (const response of denied) {
    assert(response.status === 403, `Expected cross-tenant 403, got ${response.status}`)
  }

  await page.setContent(`
    <main style="font-family: system-ui; padding: 24px;">
      <h1>Customer Assistant Ownership + Redaction UAT</h1>
      <p>Owner session: ${sessionId}</p>
      <p>Denied probes: ${denied.length}</p>
      <p>Redaction markers: present</p>
    </main>
  `)
  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })

  console.log('PASS customer assistant redaction ownership boundary e2e')
} finally {
  await browser.close()
}
