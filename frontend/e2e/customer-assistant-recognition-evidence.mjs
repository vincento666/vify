import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const hostContext = {
  apiBaseUrl: '/api',
  actorId: 'operator-094-uat',
  actorName: 'Recognition Evidence Operator',
  tenantId: 'tenant-094-uat',
  orgId: 'org-094-uat',
  permissions: ['customer_assistant:read', 'customer_assistant:operate'],
  source: 'embedded-demo-shell',
  requestId: 'req-094-uat',
}

const hostReadHeaders = {
  'Content-Type': 'application/json',
  'X-Hify-Actor-Id': hostContext.actorId,
  'X-Hify-Actor-Name': hostContext.actorName,
  'X-Hify-Tenant-Id': hostContext.tenantId,
  'X-Hify-Org-Id': hostContext.orgId,
  'X-Hify-Source': hostContext.source,
  'X-Hify-Permissions': 'customer_assistant:read',
  'X-Request-Id': hostContext.requestId,
}

async function api(page, path, options = {}) {
  return page.evaluate(
    async ({ path, options }) => {
      const response = await fetch(`/api/v1${path}`, {
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
        ...options,
      })
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
const page = await browser.newPage({ viewport: { width: 1280, height: 820 } })

try {
  await page.addInitScript((context) => {
    globalThis.__HIFY_HOST__ = context
  }, hostContext)

  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })

  await page.getByLabel('客户侧输入模拟').fill('手机号 13800138000，我要退票')
  await page.getByRole('button', { name: /模拟客户输入/ }).click()

  const evidencePanel = page.getByTestId('operator-recognition-evidence-panel')
  await evidencePanel.getByText('refund_ticket_chatflow').waitFor({ state: 'visible', timeout: 15000 })
  await evidencePanel.getByText('customer_assistant_chatflow_default').waitFor({ state: 'visible', timeout: 15000 })
  await evidencePanel.getByText('manual_confirm').waitFor({ state: 'visible', timeout: 15000 })

  const evidenceText = await evidencePanel.textContent()
  assert(evidenceText && evidenceText.includes('refund_ticket'), 'Expected recognized refund task in evidence panel')
  assert(!evidenceText.includes('13800138000'), 'Recognition evidence panel must not expose customer phone')

  const sessionMeta = await page.locator('.workspace-meta').textContent()
  const sessionIdMatch = /Session #(\d+)/.exec(sessionMeta || '')
  assert(sessionIdMatch, `Expected session id in workspace meta, got ${sessionMeta}`)
  const sessionId = Number(sessionIdMatch[1])
  const eventResult = await api(page, `/customer-assistant/sessions/${sessionId}/events`, {
    headers: hostReadHeaders,
  })
  assert(eventResult.ok, `Expected events success, got ${eventResult.status}`)
  const taskRecognized = eventResult.body.data.list.find((event) => event.type === 'task_recognized')
  assert(taskRecognized, 'Expected task_recognized event')
  const command = taskRecognized.payload.commands[0]
  assert(command.profileRefs.profileId === 'refund_ticket_chatflow', 'Expected profile id in recognition event')
  assert(command.profileRefs.riskPolicyRef === 'manual_confirm', 'Expected risk policy in recognition event')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant recognition evidence e2e')
} finally {
  await browser.close()
}
