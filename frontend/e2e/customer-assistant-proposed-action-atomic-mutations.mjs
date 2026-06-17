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
    'X-Hify-Actor-Id': `operator-142-${stamp}`,
    'X-Hify-Actor-Name': 'Operator 142',
    'X-Hify-Tenant-Id': `tenant-142-${stamp}`,
    'X-Hify-Org-Id': `tenant-142-${stamp}`,
    'X-Hify-Source': 'embedded-demo-shell',
    'X-Hify-Permissions': 'customer_assistant:read,customer_assistant:operate',
    'X-Request-Id': `req-142-${stamp}`,
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

async function createRefundAction(page, headers) {
  const created = await api(page, '/customer-assistant/sessions', {
    method: 'POST',
    headers,
    body: JSON.stringify({ context: { customerId: `C-142-${stamp}` } }),
  })
  assert(created.ok, `Expected session create success, got ${created.status}`)
  const sessionId = created.body.data.id

  for (const [index, message] of ['我要退票', '订单号 TK-142 手机号 13800138000', '确认'].entries()) {
    const turn = await api(page, `/customer-assistant/sessions/${sessionId}/turns`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message, idempotencyKey: `uat-142-${stamp}-${index}` }),
    })
    assert(turn.ok, `Expected refund turn ${index} success, got ${turn.status}`)
    const action = turn.body.data.proposedActions?.[0]
    if (action) return { sessionId, actionId: action.id }
  }
  throw new Error('Expected refund proposed action')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 760 } })
const headers = hostHeaders()

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  const { sessionId, actionId } = await createRefundAction(page, headers)

  const [confirmResult, rejectResult] = await Promise.all([
    api(page, `/customer-assistant/proposed-actions/${actionId}/confirm`, { method: 'POST', headers }),
    api(page, `/customer-assistant/proposed-actions/${actionId}/reject`, { method: 'POST', headers }),
  ])
  const mutationResults = [confirmResult, rejectResult]
  const successes = mutationResults.filter((result) => result.ok)
  const failures = mutationResults.filter((result) => !result.ok)
  assert(successes.length === 1, `Expected one successful terminal mutation, got ${successes.length}`)
  assert(failures.length === 1, `Expected one stale mutation failure, got ${failures.length}`)
  assert([400, 409].includes(failures[0].status), `Expected stale mutation HTTP 400/409, got ${failures[0].status}`)

  const actions = await api(page, `/customer-assistant/sessions/${sessionId}/proposed-actions`, { headers })
  assert(actions.ok, `Expected proposed action list success, got ${actions.status}`)
  const action = actions.body.data.list.find((item) => item.id === actionId)
  assert(action, 'Expected action after concurrent mutation')
  assert(['CONFIRMED', 'REJECTED'].includes(action.status), `Expected terminal status, got ${action.status}`)

  const audit = await api(page, `/customer-assistant/sessions/${sessionId}/operator-audit`, { headers })
  assert(audit.ok, `Expected operator audit success, got ${audit.status}`)
  const terminalRows = audit.body.data.list.filter((row) =>
    ['proposed_action_confirmed', 'proposed_action_rejected'].includes(row.eventType),
  )
  assert(terminalRows.length === 1, `Expected exactly one terminal audit row, got ${terminalRows.length}`)
  assert(terminalRows[0].actor === 'operator', `Expected operator actor, got ${terminalRows[0].actor}`)
  assert(
    terminalRows[0].source === 'operator_advisory',
    `Expected operator_advisory source, got ${terminalRows[0].source}`,
  )

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant proposed action atomic mutations browser uat')
} finally {
  await browser.close()
}
