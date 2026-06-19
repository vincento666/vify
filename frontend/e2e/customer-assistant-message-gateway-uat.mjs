import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const artifactDir = process.env.HIFY_E2E_ARTIFACT_DIR
  || '/Users/vincento/work/develop/hify/artifacts/slices/198-customer-assistant-session-message-gateway/198.1'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || join(artifactDir, 'screenshots')
const reportPath = process.env.HIFY_E2E_REPORT || join(artifactDir, 'customer-assistant-message-gateway-uat.json')

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

async function getSseEvent(page, path, label) {
  const text = await (await page.request.get(`${baseUrl}${path}`)).text()
  const dataLine = text.split('\n').find((line) => line.startsWith('data:'))
  assert(dataLine, `${label} should return an SSE data frame: ${text}`)
  return JSON.parse(dataLine.slice('data:'.length).trim())
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 860 } })

try {
  await mkdir(screenshotDir, { recursive: true })
  const stamp = Date.now()
  const first = await requestJson(page, '/api/v1/customer-assistant/messages', {
    message: '我要退票',
    idempotencyKey: `customer-message-gateway-uat-first-${stamp}`,
  }, 'send first customer assistant message')
  const second = await requestJson(page, `/api/v1/customer-assistant/sessions/${first.sessionId}/messages`, {
    message: '订单号 TK-100',
    idempotencyKey: `customer-message-gateway-uat-second-${stamp}`,
  }, 'send second customer assistant message')
  const replay = await requestJson(page, `/api/v1/customer-assistant/sessions/${first.sessionId}/messages`, {
    message: '订单号 TK-100',
    idempotencyKey: `customer-message-gateway-uat-second-${stamp}`,
  }, 'replay second customer assistant message')
  const events = await getJson(page, `/api/v1/customer-assistant/sessions/${first.sessionId}/events`, 'get session events')
  const delta = events.list.find((event) => event.type === 'message.delta')
  const completed = events.list.find((event) => event.type === 'message.completed')
  const requiresInput = events.list.find((event) => event.type === 'requires_input')
  const runCompleted = events.list.find((event) => event.type === 'run.completed')
  const recovered = await getSseEvent(
    page,
    `/api/v1/customer-assistant/sessions/${first.sessionId}/events/stream?afterSequence=${delta.sequence}&_testLimit=1`,
    'recover after message delta',
  )

  assert(first.sessionId, `first message should create session: ${JSON.stringify(first)}`)
  assert(first.conversationId === `customer-assistant:${first.sessionId}`, `unexpected conversation id: ${JSON.stringify(first)}`)
  assert(first.eventStreamRef.endsWith('afterSequence=0'), `unexpected event stream ref: ${first.eventStreamRef}`)
  assert(second.sessionId === first.sessionId, `second message should reuse session: ${JSON.stringify(second)}`)
  assert(second.conversationId === first.conversationId, `conversation should stay stable: ${JSON.stringify(second)}`)
  assert(replay.runId === second.runId && replay.replayed === true, `replay should reuse second run: ${JSON.stringify(replay)}`)
  assert(delta && completed && requiresInput && runCompleted, `missing projected event types: ${JSON.stringify(events)}`)
  assert(completed.payload.answer === first.answer, `completed event should expose answer: ${JSON.stringify(completed)}`)
  assert(recovered.type === 'message.completed', `afterSequence recovery should return message.completed: ${JSON.stringify(recovered)}`)

  const report = {
    first,
    second,
    replay,
    eventTypes: events.list.map((event) => event.type),
    eventsTotal: events.total,
    recovered,
  }
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`)
  await page.setContent(`
    <main style="font-family: system-ui; padding: 2rem; line-height: 1.45;">
      <h1>Customer Assistant Message Gateway UAT</h1>
      <p>Session ${first.sessionId}</p>
      <p>Conversation ${first.conversationId}</p>
      <p>Status ${first.status}</p>
      <p>Answer ${first.answer}</p>
      <p>Recovered ${recovered.type}</p>
      <p>Events ${events.total}</p>
    </main>
  `)
  const screenshot = join(screenshotDir, 'customer-assistant-message-gateway.png')
  await page.screenshot({ path: screenshot, fullPage: true })
  console.log(`PASS customer assistant message gateway UAT session=${first.sessionId} screenshot=${screenshot}`)
} finally {
  await browser.close()
}
