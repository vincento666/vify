import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const artifactDir = process.env.HIFY_E2E_ARTIFACT_DIR || '/Users/vincento/work/develop/hify/artifacts/slices/197-runtime-lab-sop-session-gateway/197.1'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || join(artifactDir, 'screenshots')
const reportPath = process.env.HIFY_E2E_REPORT || join(artifactDir, 'runtime-lab-sop-router-session-gateway-uat.json')

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  const text = await response.text()
  let payload = {}
  try {
    payload = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`${label} returned non-JSON HTTP ${response.status()}: ${text}`)
  }
  assert(response.ok(), `${label} HTTP ${response.status()}: ${text}`)
  assert(payload.code === 200, `${label} API ${payload.message || text}`)
  return payload.data
}

async function requestJson(page, path, data, label) {
  return unwrap(await page.request.post(`${baseUrl}${path}`, { data }), label)
}

async function getJson(page, path, label) {
  return unwrap(await page.request.get(`${baseUrl}${path}`), label)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 860 } })

try {
  await mkdir(screenshotDir, { recursive: true })
  const stamp = Date.now()
  const first = await requestJson(page, '/api/v1/runtime-lab/messages', {
    message: '我要退票',
    idempotencyKey: `runtime-lab-gateway-uat-first-${stamp}`,
  }, 'send first SOP message')
  const second = await requestJson(page, '/api/v1/runtime-lab/messages', {
    sessionId: first.sessionId,
    message: '订单号 CA1001',
    idempotencyKey: `runtime-lab-gateway-uat-second-${stamp}`,
  }, 'send second SOP message')
  const events = await getJson(page, `/api/v1/runtime-lab/sessions/${first.sessionId}/events`, 'get runtime lab events')

  assert(first.sessionId, `first turn should auto-create session: ${JSON.stringify(first)}`)
  assert(first.conversationId === `runtime-lab:${first.sessionId}`, `unexpected conversation id: ${JSON.stringify(first)}`)
  assert(first.currentSopId === 'refund_ticket', `first turn should route refund SOP: ${JSON.stringify(first)}`)
  assert(first.intent === 'refund_ticket', `first turn should expose intent: ${JSON.stringify(first)}`)
  assert(typeof first.answer === 'string' && first.answer.length > 0, `first turn should expose answer: ${JSON.stringify(first)}`)
  assert(Number.isInteger(first.latencyMs) && first.latencyMs >= 0, `first turn should expose latency: ${JSON.stringify(first)}`)
  assert(second.sessionId === first.sessionId, `second turn should reuse session: ${JSON.stringify(second)}`)
  assert(second.conversationId === first.conversationId, `second turn should keep conversation: ${JSON.stringify(second)}`)
  assert(typeof second.answer === 'string' && second.answer.length > 0, `second turn should expose answer: ${JSON.stringify(second)}`)
  const eventTypes = events.list.map((event) => event.eventType)
  assert(eventTypes.includes('SESSION_CREATED'), `missing session created event: ${JSON.stringify(events)}`)
  assert(eventTypes.includes('USER_MESSAGE'), `missing user message event: ${JSON.stringify(events)}`)
  assert(eventTypes.includes('ROUTE_DECISION'), `missing route decision event: ${JSON.stringify(events)}`)

  const report = {
    first,
    second,
    eventTypes,
    eventsTotal: events.total,
  }
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`)
  await page.setContent(`
    <main style="font-family: system-ui; padding: 2rem; line-height: 1.45;">
      <h1>Runtime Lab SOP Session Gateway UAT</h1>
      <p>Session ${first.sessionId}</p>
      <p>SOP ${first.currentSopId}</p>
      <p>Intent ${first.intent}</p>
      <p>Status ${second.status}</p>
      <p>Events ${events.total}</p>
    </main>
  `)
  const screenshot = join(screenshotDir, 'runtime-lab-sop-router-session-gateway.png')
  await page.screenshot({ path: screenshot, fullPage: true })
  console.log(`PASS runtime lab SOP session gateway UAT session=${first.sessionId} screenshot=${screenshot}`)
} finally {
  await browser.close()
}
