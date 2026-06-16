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
    body: JSON.stringify({ context: { source: 'proposed-action-edit-e2e' } }),
  })
  assert(created.ok, `Expected session create success, got ${created.status}`)
  const sessionId = created.body.data.id

  const turn = await api(page, `/customer-assistant/sessions/${sessionId}/turns`, {
    method: 'POST',
    body: JSON.stringify({ message: '我要退票', idempotencyKey: 'proposed-action-edit-e2e-turn' }),
  })
  assert(turn.ok, `Expected turn success, got ${turn.status}`)

  const tasks = await api(page, `/customer-assistant/sessions/${sessionId}/tasks`)
  const task = tasks.body.data.list[0]
  assert(task, 'Expected a task to propose a control action')
  const controlType = task.status === 'FAILED' ? 'retry' : task.status === 'WAITING' ? 'resume' : 'cancel'

  const proposed = await api(page, `/customer-assistant/sessions/${sessionId}/tasks/${task.id}/controls/propose`, {
    method: 'POST',
    body: JSON.stringify({ controlType, reason: 'browser UAT before edit' }),
  })
  assert(proposed.ok, `Expected proposed control success, got ${proposed.status}: ${JSON.stringify(proposed.body)}`)
  const action = proposed.body.data

  const edited = await api(page, `/customer-assistant/proposed-actions/${action.id}`, {
    method: 'PATCH',
    body: JSON.stringify({
      title: `${action.title}（坐席已复核）`,
      payload: { ...action.payload, reason: 'browser UAT edited reason' },
    }),
  })
  assert(edited.ok, `Expected proposed action edit success, got ${edited.status}`)
  assert(edited.body.data.status === 'PENDING', 'Expected edited action to remain pending')
  assert(edited.body.data.title.includes('坐席已复核'), 'Expected edited title')
  assert(edited.body.data.payload.reason === 'browser UAT edited reason', 'Expected edited payload reason')

  const confirmed = await api(page, `/customer-assistant/proposed-actions/${action.id}/confirm`, { method: 'POST' })
  assert(confirmed.ok, `Expected confirm success, got ${confirmed.status}`)
  assert(confirmed.body.data.status === 'CONFIRMED', 'Expected confirmed edited action')

  const events = await api(page, `/customer-assistant/sessions/${sessionId}/events`)
  const eventTypes = events.body.data.list.map((event) => event.type)
  assert(eventTypes.includes('proposed_action_modified'), 'Expected modification audit event')
  assert(eventTypes.includes('proposed_task_command_confirmed'), 'Expected confirm audit event')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant proposed action edit api e2e')
} finally {
  await browser.close()
}
