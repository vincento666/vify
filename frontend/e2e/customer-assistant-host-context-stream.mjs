import { mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const calls = []

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function rememberCustomerAssistantCall(request) {
  const url = request.url()
  if (!url.includes('/api/v1/customer-assistant/')) return
  calls.push({
    method: request.method(),
    url,
    headers: request.headers(),
    body: request.postDataJSON?.(),
  })
}

function header(call, name) {
  return call.headers[name.toLowerCase()]
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
page.on('request', rememberCustomerAssistantCall)

try {
  await page.addInitScript(() => {
    globalThis.__HIFY_HOST__ = {
      apiBaseUrl: '/api',
      actorId: 'operator-0783-uat',
      actorName: 'Host Context Operator',
      tenantId: 'tenant-0783-uat',
      orgId: 'org-0783-uat',
      permissions: ['customer_assistant:read', 'customer_assistant:operate'],
      source: 'embedded-demo-shell',
      requestId: 'req-0783-uat',
    }
  })

  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('button', { name: '模拟客户输入' }).click()

  await page.getByText(/Session #\d+/).waitFor({ state: 'visible', timeout: 10000 })
  await page
    .getByTestId('operator-task-ledger')
    .locator('.task-row')
    .filter({ hasText: 'refund_ticket ·' })
    .first()
    .waitFor({ state: 'visible', timeout: 10000 })

  const sessionCall = calls.find((call) => call.method === 'POST' && call.url.endsWith('/sessions'))
  assert(sessionCall, 'Expected session creation request')
  assert(header(sessionCall, 'X-Hify-Actor-Id') === 'operator-0783-uat', 'Expected session actor header')
  assert(header(sessionCall, 'X-Hify-Tenant-Id') === 'tenant-0783-uat', 'Expected session tenant header')
  assert(
    header(sessionCall, 'X-Hify-Permissions') === 'customer_assistant:read,customer_assistant:operate',
    'Expected session permission header',
  )

  const streamCall = calls.find((call) => call.method === 'GET' && call.url.includes('/events/stream'))
  assert(streamCall, 'Expected authenticated customer assistant event stream request')
  assert(header(streamCall, 'Accept') === 'text/event-stream', 'Expected stream accept header')
  assert(header(streamCall, 'X-Hify-Actor-Id') === 'operator-0783-uat', 'Expected stream actor header')
  assert(header(streamCall, 'X-Hify-Tenant-Id') === 'tenant-0783-uat', 'Expected stream tenant header')
  assert(header(streamCall, 'X-Hify-Org-Id') === 'org-0783-uat', 'Expected stream org header')
  assert(
    header(streamCall, 'X-Hify-Permissions') === 'customer_assistant:read,customer_assistant:operate',
    'Expected stream permission header',
  )
  assert(header(streamCall, 'X-Request-Id') === 'req-0783-uat', 'Expected stream request id header')

  if (screenshotPath) {
    mkdirSync(dirname(screenshotPath), { recursive: true })
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant host context stream e2e')
} finally {
  page.off('request', rememberCustomerAssistantCall)
  await browser.close()
}
