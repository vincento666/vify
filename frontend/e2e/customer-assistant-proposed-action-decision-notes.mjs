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
    'X-Hify-Actor-Id': `operator-143-${stamp}`,
    'X-Hify-Actor-Name': 'Operator 143',
    'X-Hify-Tenant-Id': `tenant-143-${stamp}`,
    'X-Hify-Org-Id': `tenant-143-${stamp}`,
    'X-Hify-Source': 'embedded-demo-shell',
    'X-Hify-Permissions': 'customer_assistant:read,customer_assistant:operate',
    'X-Request-Id': `req-143-${stamp}`,
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

  for (const [index, message] of ['我要退票', '订单号 TK-143 手机号 13800138000', '确认'].entries()) {
    const turn = await api(page, `/customer-assistant/sessions/${sessionId}/turns`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message, idempotencyKey: `${prefix}-${index}` }),
    })
    assert(turn.ok, `Expected refund turn ${index} success, got ${turn.status}`)
    const action = turn.body.data.proposedActions?.[0]
    if (action) return { sessionId, actionId: action.id }
  }
  throw new Error('Expected refund proposed action')
}

function assertDecisionText(result, field, expected) {
  assert(result.body.data.result?.decision?.[field] === expected, `Expected ${field} decision text`)
}

function assertNoRawSensitiveText(publicBody) {
  const serialized = JSON.stringify(publicBody)
  for (const leaked of ['13800138000', '13900139000', 'TK-143', 'TK-144', 'note-secret', 'reject-secret']) {
    assert(!serialized.includes(leaked), `Expected public body not to leak ${leaked}`)
  }
}

const note = 'confirmed by phone 13800138000 for order TK-143 apiKey=note-secret'
const reason = 'operator refused phone 13900139000 order TK-144 token=reject-secret'
const expectedNote = 'confirmed by phone [REDACTED] for order [REDACTED] apiKey=***'
const expectedReason = 'operator refused phone [REDACTED] order [REDACTED] token=***'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 760 } })
const headers = hostHeaders()

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })

  const confirmFlow = await createRefundAction(page, headers, `uat-143-confirm-${stamp}`)
  const confirmed = await api(page, `/customer-assistant/proposed-actions/${confirmFlow.actionId}/confirm`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ note }),
  })
  assert(confirmed.ok, `Expected action confirm success, got ${confirmed.status}`)
  assertDecisionText(confirmed, 'note', expectedNote)

  const rejectFlow = await createRefundAction(page, headers, `uat-143-reject-${stamp}`)
  const rejected = await api(page, `/customer-assistant/proposed-actions/${rejectFlow.actionId}/reject`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ reason }),
  })
  assert(rejected.ok, `Expected action reject success, got ${rejected.status}`)
  assertDecisionText(rejected, 'reason', expectedReason)

  const confirmEvents = await api(page, `/customer-assistant/sessions/${confirmFlow.sessionId}/events`, { headers })
  assert(confirmEvents.ok, `Expected confirm events success, got ${confirmEvents.status}`)
  const confirmedEvent = confirmEvents.body.data.list.find((event) => event.type === 'proposed_action_confirmed')
  assert(confirmedEvent?.payload?.decision?.note === expectedNote, 'Expected confirmed event decision note')

  const rejectEvents = await api(page, `/customer-assistant/sessions/${rejectFlow.sessionId}/events`, { headers })
  assert(rejectEvents.ok, `Expected reject events success, got ${rejectEvents.status}`)
  const rejectedEvent = rejectEvents.body.data.list.find((event) => event.type === 'proposed_action_rejected')
  assert(rejectedEvent?.payload?.decision?.reason === expectedReason, 'Expected rejected event decision reason')

  const confirmAudit = await api(page, `/customer-assistant/sessions/${confirmFlow.sessionId}/operator-audit`, {
    headers,
  })
  assert(confirmAudit.ok, `Expected confirm audit success, got ${confirmAudit.status}`)
  const confirmRow = confirmAudit.body.data.list.find((row) => row.eventType === 'proposed_action_confirmed')
  assert(confirmRow?.summary?.includes(`note: ${expectedNote}`), 'Expected confirm audit note summary')

  const rejectAudit = await api(page, `/customer-assistant/sessions/${rejectFlow.sessionId}/operator-audit`, {
    headers,
  })
  assert(rejectAudit.ok, `Expected reject audit success, got ${rejectAudit.status}`)
  const rejectRow = rejectAudit.body.data.list.find((row) => row.eventType === 'proposed_action_rejected')
  assert(rejectRow?.summary?.includes(`reason: ${expectedReason}`), 'Expected reject audit reason summary')

  assertNoRawSensitiveText({
    confirmed: confirmed.body,
    rejected: rejected.body,
    confirmEvents: confirmEvents.body,
    rejectEvents: rejectEvents.body,
    confirmAudit: confirmAudit.body,
    rejectAudit: rejectAudit.body,
  })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant proposed action decision notes browser uat')
} finally {
  await browser.close()
}
