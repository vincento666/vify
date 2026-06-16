import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function api(page, method, path, data) {
  return page.evaluate(
    async ({ method: requestMethod, path: requestPath, data: requestData }) => {
      const response = await fetch(requestPath, {
        method: requestMethod,
        headers: requestData === undefined ? {} : { 'Content-Type': 'application/json' },
        body: requestData === undefined ? undefined : JSON.stringify(requestData),
      })
      return { status: response.status, payload: await response.json() }
    },
    { method, path, data },
  )
}

function unwrap(response, label) {
  assert(response.status === 200, `${label} HTTP ${response.status}`)
  assert(response.payload.code === 200, `${label} API ${response.payload.message}`)
  return response.payload.data
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  const stamp = Date.now()
  const chatflow = unwrap(await api(page, 'POST', '/api/v1/chatflows', {
    name: `Runtime V2 Cancel UAT ${stamp}`,
    description: 'runtime v2 cancel lifecycle browser UAT',
    nodes: [
      { nodeKey: 'start', type: 'START', name: 'Start', config: {} },
      {
        nodeKey: 'message_1',
        type: 'MESSAGE',
        name: 'Message',
        config: { content: 'Hello {{start.sys.query}}', outputVariable: 'content' },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: 'End',
        config: { outputVariable: 'final', output: 'sent: {{message_1.content}}' },
      },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'message_1', condition: null },
      { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
    ],
  }), 'create chatflow')

  const started = unwrap(await api(page, 'POST', `/api/v1/chatflows/${chatflow.id}/runs-v2`, {
    input: { 'sys.query': 'Ada', callerContext: { uat: 'runtime-v2-cancel' } },
  }), 'start runtime v2 run')

  const cancelled = unwrap(
    await api(page, 'POST', `/api/v1/runtime-runs/${started.runId}/cancel`),
    'cancel runtime v2 run',
  )
  await page.waitForTimeout(700)
  const terminal = unwrap(
    await api(page, 'GET', `/api/v1/runtime-runs/${started.runId}/result`),
    'get runtime v2 result',
  )
  const events = unwrap(
    await api(page, 'GET', `/api/v1/runtime-runs/${started.runId}/events`),
    'list runtime v2 events',
  )
  const eventTypes = events.list.map((event) => event.type)

  assert(cancelled.status === 'CANCELLED', `Expected cancel response CANCELLED, got ${cancelled.status}`)
  assert(cancelled.cancellation?.applied === true, 'Expected cancellation to be applied')
  assert(terminal.status === 'CANCELLED', `Expected durable CANCELLED result, got ${terminal.status}`)
  assert(eventTypes.includes('workflow_run_cancelled'), `Expected workflow_run_cancelled in ${eventTypes.join(',')}`)
  assert(!eventTypes.includes('workflow_run_completed'), 'Cancelled run must not publish completion event')

  if (screenshotPath) {
    await page.setContent(`
      <main style="font-family: system-ui; padding: 2rem; line-height: 1.5;">
        <h1>Runtime v2 cancel UAT</h1>
        <p>Chatflow #${chatflow.id}, Run #${started.runId}</p>
        <p>Status: <strong>${terminal.status}</strong></p>
        <p>Events: ${eventTypes.join(', ')}</p>
      </main>
    `)
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS runtime v2 cancel lifecycle chatflow=${chatflow.id} run=${started.runId}`)
} finally {
  await browser.close()
}
