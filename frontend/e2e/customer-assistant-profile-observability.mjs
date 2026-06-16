import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
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
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } })

try {
  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })

  const created = await api(page, '/customer-assistant/sessions', {
    method: 'POST',
    body: JSON.stringify({ context: { source: 'profile-observability-e2e' } }),
  })
  assert(created.ok, `Expected session create success, got ${created.status}`)
  const sessionId = created.body.data.id

  const turn = await api(page, `/customer-assistant/sessions/${sessionId}/turns`, {
    method: 'POST',
    body: JSON.stringify({ message: '我要退票', idempotencyKey: 'profile-observability-e2e' }),
  })
  assert(turn.ok, `Expected turn success, got ${turn.status}`)

  const eventResult = await api(page, `/customer-assistant/sessions/${sessionId}/events`)
  assert(eventResult.ok, `Expected events success, got ${eventResult.status}`)
  const events = eventResult.body.data.list
  const taskStarted = events.find((event) => event.type === 'task_started')
  assert(taskStarted, 'Expected task_started event')
  assert(taskStarted.payload.profileRefs.profileId === 'refund_ticket_chatflow', 'Expected profile id in event payload')
  assert(
    taskStarted.observability.profileRefs.profileId === 'refund_ticket_chatflow',
    'Expected profile id in event observability',
  )
  assert(
    taskStarted.observability.profileRefs.riskPolicyRef === 'manual_confirm',
    'Expected risk policy in event observability',
  )

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant profile observability e2e')
} finally {
  await browser.close()
}
