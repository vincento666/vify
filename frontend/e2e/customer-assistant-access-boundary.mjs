import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const hostBaseHeaders = {
  'Content-Type': 'application/json',
  'X-Hify-Actor-Id': 'operator-078-uat',
  'X-Hify-Actor-Name': 'Access Boundary Operator',
  'X-Hify-Tenant-Id': 'tenant-078-uat',
  'X-Hify-Org-Id': 'org-078-uat',
  'X-Hify-Source': 'embedded-demo-shell',
  'X-Request-Id': 'req-078-uat',
}

const hostReadHeaders = {
  ...hostBaseHeaders,
  'X-Hify-Permissions': 'customer_assistant:read',
}

const hostOperateHeaders = {
  ...hostBaseHeaders,
  'X-Hify-Permissions': 'customer_assistant:read,customer_assistant:operate',
}

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

  const deniedRead = await api(page, '/customer-assistant/worker-profiles', {
    headers: {
      ...hostBaseHeaders,
      'X-Hify-Permissions': 'workflow:run',
    },
  })
  assert(deniedRead.status === 403, `Expected read 403, got ${deniedRead.status}`)
  assert(
    deniedRead.body.message.includes('customer_assistant:read'),
    `Expected read permission message, got ${deniedRead.body.message}`,
  )

  const deniedOperate = await api(page, '/customer-assistant/sessions', {
    method: 'POST',
    headers: hostReadHeaders,
    body: JSON.stringify({ context: { customerId: 'C-UAT' } }),
  })
  assert(deniedOperate.status === 403, `Expected operate 403, got ${deniedOperate.status}`)
  assert(
    deniedOperate.body.message.includes('customer_assistant:operate'),
    `Expected operate permission message, got ${deniedOperate.body.message}`,
  )

  const created = await api(page, '/customer-assistant/sessions', {
    method: 'POST',
    headers: hostOperateHeaders,
    body: JSON.stringify({
      context: {
        customer: { phone: '13800138000', orderNo: 'TK-100' },
        debug: 'token=browser-uat-token',
        apiToken: 'browser-api-token',
      },
    }),
  })
  assert(created.ok, `Expected allowed create, got ${created.status}`)
  const contextText = JSON.stringify(created.body.data.context)
  assert(created.body.data.context.hostContext.tenantId === 'tenant-078-uat', 'Expected tenant in host context')
  assert(created.body.data.context.hostContext.actorId === 'operator-078-uat', 'Expected actor in host context')
  assert(!contextText.includes('13800138000'), 'Session context must redact phone')
  assert(!contextText.includes('TK-100'), 'Session context must redact order number')
  assert(!contextText.includes('browser-uat-token'), 'Session context must redact token assignment')
  assert(!contextText.includes('browser-api-token'), 'Session context must redact apiToken value')

  const sessionId = created.body.data.id
  const turn = await api(page, `/customer-assistant/sessions/${sessionId}/turns`, {
    method: 'POST',
    headers: hostOperateHeaders,
    body: JSON.stringify({ message: '我要退票', idempotencyKey: 'access-boundary-browser' }),
  })
  assert(turn.ok, `Expected allowed turn, got ${turn.status}`)
  assert(turn.body.data.taskSummaries[0].taskKey === 'refund_ticket', 'Expected refund task recognition')

  const metrics = await api(page, `/customer-assistant/sessions/${sessionId}/metrics`, {
    headers: hostReadHeaders,
  })
  assert(metrics.ok, `Expected metrics read, got ${metrics.status}`)
  assert(metrics.body.data.sessionId === sessionId, 'Expected metrics for created session')

  await page.setContent(`
    <main style="font-family: system-ui; padding: 24px;">
      <h1>Customer Assistant Access Boundary UAT</h1>
      <p>Denied read: ${deniedRead.status}</p>
      <p>Denied operate: ${deniedOperate.status}</p>
      <p>Allowed session: ${sessionId}</p>
      <p>Metrics events: ${metrics.body.data.eventCounts.total}</p>
    </main>
  `)
  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })

  console.log('PASS customer assistant access boundary e2e')
} finally {
  await browser.close()
}
