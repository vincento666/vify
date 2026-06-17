import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const stamp = Date.now()

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function hostHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-Hify-Actor-Id': `operator-141-${stamp}`,
    'X-Hify-Actor-Name': 'Operator 141',
    'X-Hify-Tenant-Id': `tenant-141-${stamp}`,
    'X-Hify-Org-Id': `tenant-141-${stamp}`,
    'X-Hify-Source': 'embedded-demo-shell',
    'X-Hify-Permissions': 'customer_assistant:read,customer_assistant:operate',
    'X-Request-Id': `req-141-${stamp}`,
  }
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

async function createRefundAction(page, headers, prefix) {
  const created = await api(page, '/customer-assistant/sessions', {
    method: 'POST',
    headers,
    body: JSON.stringify({ context: { customerId: `C-${prefix}` } }),
  })
  assert(created.ok, `Expected session create success, got ${created.status}`)
  const sessionId = created.body.data.id

  const first = await api(page, `/customer-assistant/sessions/${sessionId}/turns`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message: '我要退票', idempotencyKey: `${prefix}-start` }),
  })
  assert(first.ok, `Expected first refund turn success, got ${first.status}`)

  const details = await api(page, `/customer-assistant/sessions/${sessionId}/turns`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message: '订单号 TK-100 手机号 13800138000', idempotencyKey: `${prefix}-details` }),
  })
  assert(details.ok, `Expected refund detail turn success, got ${details.status}`)

  const completed = await api(page, `/customer-assistant/sessions/${sessionId}/turns`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message: '确认', idempotencyKey: `${prefix}-complete` }),
  })
  assert(completed.ok, `Expected refund completion turn success, got ${completed.status}`)
  const action = completed.body.data.proposedActions[0] || details.body.data.proposedActions[0]
  assert(action, 'Expected submit_refund proposed action')
  return { sessionId, actionId: action.id }
}

function assertAuditAttribution(rows, expectedTypes) {
  const matched = rows.filter((row) => expectedTypes.includes(row.eventType))
  assert(matched.length === expectedTypes.length, `Expected audit rows ${expectedTypes.join(', ')}`)
  for (const row of matched) {
    assert(row.actor === 'operator', `Expected operator actor for ${row.eventType}, got ${row.actor}`)
    assert(
      row.source === 'operator_advisory',
      `Expected operator_advisory source for ${row.eventType}, got ${row.source}`,
    )
  }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 760 } })
const headers = hostHeaders()

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })

  const executeFlow = await createRefundAction(page, headers, `uat-141-execute-${stamp}`)
  const confirmed = await api(page, `/customer-assistant/proposed-actions/${executeFlow.actionId}/confirm`, {
    method: 'POST',
    headers,
  })
  assert(confirmed.ok, `Expected action confirm success, got ${confirmed.status}`)
  const executed = await api(page, `/customer-assistant/proposed-actions/${executeFlow.actionId}/execute`, {
    method: 'POST',
    headers,
  })
  assert(executed.ok, `Expected action execute success, got ${executed.status}`)

  const rejectFlow = await createRefundAction(page, headers, `uat-141-reject-${stamp}`)
  const rejected = await api(page, `/customer-assistant/proposed-actions/${rejectFlow.actionId}/reject`, {
    method: 'POST',
    headers,
  })
  assert(rejected.ok, `Expected action reject success, got ${rejected.status}`)

  const executeAudit = await api(page, `/customer-assistant/sessions/${executeFlow.sessionId}/operator-audit`, {
    headers,
  })
  assert(executeAudit.ok, `Expected execute audit success, got ${executeAudit.status}`)
  assertAuditAttribution(executeAudit.body.data.list, [
    'proposed_action_confirmed',
    'proposed_action_executing',
    'proposed_action_executed',
  ])

  const rejectAudit = await api(page, `/customer-assistant/sessions/${rejectFlow.sessionId}/operator-audit`, {
    headers,
  })
  assert(rejectAudit.ok, `Expected reject audit success, got ${rejectAudit.status}`)
  assertAuditAttribution(rejectAudit.body.data.list, ['proposed_action_rejected'])

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant proposed action operator attribution browser uat')
} finally {
  await browser.close()
}
