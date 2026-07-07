import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const artifactDir = process.env.HIFY_E2E_ARTIFACT_DIR
  || '/Users/vincento/work/develop/hify/artifacts/slices/207-final-uat-gates/207.1'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || join(artifactDir, 'screenshots')
const reportPath = process.env.HIFY_E2E_REPORT || join(artifactDir, 'customer-assistant-chatflow-runtime-gateway-uat.json')

const hostContext = {
  apiBaseUrl: '/api',
  actorId: 'operator-207-uat',
  actorName: 'Final UAT Operator',
  tenantId: 'tenant-207-uat',
  orgId: 'org-207-uat',
  permissions: ['customer_assistant:read', 'customer_assistant:operate'],
  source: 'embedded-final-uat',
  requestId: 'req-207-customer-assistant-uat',
}

const hostHeaders = {
  'Content-Type': 'application/json',
  'X-Hify-Actor-Id': hostContext.actorId,
  'X-Hify-Actor-Name': hostContext.actorName,
  'X-Hify-Tenant-Id': hostContext.tenantId,
  'X-Hify-Org-Id': hostContext.orgId,
  'X-Hify-Permissions': hostContext.permissions.join(','),
  'X-Request-Id': hostContext.requestId,
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function withParam(path, key, value) {
  return `${path}${path.includes('?') ? '&' : '?'}${key}=${encodeURIComponent(value)}`
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

async function postJson(page, path, data, label) {
  return unwrap(await page.request.post(`${baseUrl}${path}`, { headers: hostHeaders, data }), label)
}

async function getJson(page, path, label) {
  return unwrap(await page.request.get(`${baseUrl}${path}`, { headers: hostHeaders }), label)
}

async function getSseFrame(page, path, label) {
  const response = await page.request.get(`${baseUrl}${path}`, {
    headers: { ...hostHeaders, Accept: 'text/event-stream' },
  })
  const text = await response.text()
  assert(response.ok(), `${label} HTTP ${response.status()}: ${text}`)
  const dataLine = text.split('\n').find((line) => line.startsWith('data:'))
  assert(dataLine, `${label} should return an SSE data frame: ${text}`)
  return JSON.parse(dataLine.slice('data:'.length).trim())
}

function header(call, name) {
  return call.headers[name.toLowerCase()]
}

function assertChatflowGateway(turn, label) {
  const runtime = turn.chatflowSession
  assert(turn.conversationId === `customer-assistant:${turn.sessionId}`, `${label} conversation id should be stable: ${JSON.stringify(turn)}`)
  assert(runtime?.gatewayMode === 'messages:stream', `${label} should expose chatflow gateway mode: ${JSON.stringify(turn)}`)
  assert(runtime.runtimeVersion === 2, `${label} should bridge runtime v2: ${JSON.stringify(runtime)}`)
  assert(Number.isInteger(runtime.runId) && runtime.runId > 0, `${label} should expose runtime run id: ${JSON.stringify(runtime)}`)
  assert(typeof runtime.statusRef === 'string' && runtime.statusRef.startsWith('/api/v1/runtime-runs/'), `${label} should expose statusRef: ${JSON.stringify(runtime)}`)
  assert(typeof runtime.eventsRef === 'string' && runtime.eventsRef.startsWith('/api/v1/runtime-runs/'), `${label} should expose eventsRef: ${JSON.stringify(runtime)}`)
  assert(typeof runtime.resultRef === 'string' && runtime.resultRef.startsWith('/api/v1/runtime-runs/'), `${label} should expose resultRef: ${JSON.stringify(runtime)}`)
  assert(typeof runtime.eventStreamRef === 'string' && runtime.eventStreamRef.includes('/events/stream'), `${label} should expose eventStreamRef: ${JSON.stringify(runtime)}`)
  assert(turn.eventSummary.every((event) => !Object.prototype.hasOwnProperty.call(event, 'payload')), `${label} eventSummary should stay compact`)
  assert(turn.retryable === false, `${label} should be non-retryable: ${JSON.stringify(turn)}`)
  return runtime
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const calls = []

page.on('request', (request) => {
  const url = request.url()
  if (!url.includes('/api/v1/customer-assistant/')) return
  calls.push({
    method: request.method(),
    url,
    headers: request.headers(),
  })
})

try {
  await mkdir(screenshotDir, { recursive: true })
  await page.addInitScript((context) => {
    localStorage.clear()
    globalThis.__HIFY_HOST__ = context
  }, hostContext)

  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ timeout: 15_000 })

  await page.getByLabel('客户侧输入模拟').fill('我要退票')
  const [uiResponse] = await Promise.all([
    page.waitForResponse((response) => (
      response.request().method() === 'POST'
      && /\/api\/v1\/customer-assistant\/sessions\/\d+\/messages$/.test(new URL(response.url()).pathname)
    ), { timeout: 30_000 }),
    page.getByRole('button', { name: '模拟客户输入' }).click(),
  ])
  const uiTurn = await unwrap(uiResponse, 'UI session message')
  await page.getByText(`Session #${uiTurn.sessionId}`).first().waitFor({ timeout: 15_000 })
  await page.getByTestId('operator-task-ledger').locator('.task-row').filter({ hasText: 'refund_ticket' }).first().waitFor({
    timeout: 15_000,
  })

  const sessionCall = calls.find((call) => call.method === 'POST' && call.url.endsWith('/sessions'))
  const sessionMessageCall = calls.find((call) => call.method === 'POST' && /\/sessions\/\d+\/messages$/.test(new URL(call.url).pathname))
  assert(sessionCall, 'UI should create a customer assistant session')
  assert(sessionMessageCall, 'UI should call the session message gateway')
  assert(!calls.some((call) => call.url.endsWith('/turns')), 'UI should not call the legacy turns endpoint')
  assert(header(sessionMessageCall, 'X-Hify-Actor-Id') === hostContext.actorId, 'UI message call should carry actor header')
  assert(header(sessionMessageCall, 'X-Hify-Tenant-Id') === hostContext.tenantId, 'UI message call should carry tenant header')
  const uiRuntime = assertChatflowGateway(uiTurn, 'UI turn')

  const stamp = Date.now()
  const first = await postJson(page, '/api/v1/customer-assistant/messages', {
    message: '我要退票',
    idempotencyKey: `customer-assistant-runtime-gateway-first-${stamp}`,
  }, 'top-level customer assistant message')
  const firstRuntime = assertChatflowGateway(first, 'top-level first turn')

  const second = await postJson(page, `/api/v1/customer-assistant/sessions/${first.sessionId}/messages`, {
    message: '订单号 TK207，手机号 13800138000，乘机人张测试',
    idempotencyKey: `customer-assistant-runtime-gateway-second-${stamp}`,
  }, 'session customer assistant message')
  const secondRuntime = assertChatflowGateway(second, 'session second turn')
  assert(secondRuntime.sessionId === firstRuntime.sessionId, `session turn should reuse chatflow session: ${JSON.stringify(secondRuntime)}`)

  const confirm = await postJson(page, `/api/v1/customer-assistant/sessions/${first.sessionId}/messages`, {
    message: '确认',
    idempotencyKey: `customer-assistant-runtime-gateway-confirm-${stamp}`,
  }, 'confirm customer assistant message')
  const confirmRuntime = assertChatflowGateway(confirm, 'confirm turn')
  assert(confirm.status === 'COMPLETED', `confirm turn should complete: ${JSON.stringify(confirm)}`)
  assert(confirmRuntime.runId === firstRuntime.runId, `confirm should keep the same runtime run: ${JSON.stringify(confirmRuntime)}`)

  const run = await getJson(page, firstRuntime.statusRef, 'get runtime run')
  const result = await getJson(page, firstRuntime.resultRef, 'get runtime result')
  const events = await getJson(page, firstRuntime.eventsRef, 'get runtime events')
  const streamFrame = await getSseFrame(page, withParam(firstRuntime.eventStreamRef, '_testLimit', '1'), 'get runtime SSE')
  const recoveryFrame = await getSseFrame(
    page,
    withParam(first.recovery.chatflowEventStreamRef, '_testLimit', '1'),
    'get recovery runtime SSE',
  )

  assert(run.ownerType === 'CHATFLOW' && run.status === 'SUCCEEDED', `runtime run should succeed: ${JSON.stringify(run)}`)
  assert(result.ownerType === 'CHATFLOW' && result.status === 'SUCCEEDED', `runtime result should succeed: ${JSON.stringify(result)}`)
  assert(result.retryable === false, `runtime result should be non-retryable: ${JSON.stringify(result)}`)
  assert(events.list.some((event) => event.source === 'chatflow_runtime_v2'), `runtime events should be v2: ${JSON.stringify(events)}`)
  assert(streamFrame.source === 'chatflow_runtime_v2', `runtime SSE should be v2: ${JSON.stringify(streamFrame)}`)
  assert(recoveryFrame.source === 'chatflow_runtime_v2', `recovery SSE should be v2: ${JSON.stringify(recoveryFrame)}`)

  const screenshot = join(screenshotDir, 'customer-assistant-chatflow-runtime-gateway.png')
  await page.waitForTimeout(6000)
  await page.screenshot({ path: screenshot, fullPage: true })
  const report = {
    ui: {
      sessionId: uiTurn.sessionId,
      runtimeVersion: uiRuntime.runtimeVersion,
      runId: uiRuntime.runId,
      endpoints: calls.map((call) => ({ method: call.method, path: new URL(call.url).pathname })),
    },
    api: {
      sessionId: first.sessionId,
      statuses: [first.status, second.status, confirm.status],
      runtimeVersion: firstRuntime.runtimeVersion,
      runId: firstRuntime.runId,
      gatewayMode: firstRuntime.gatewayMode,
      statusRef: firstRuntime.statusRef,
      eventsRef: firstRuntime.eventsRef,
      eventStreamRef: firstRuntime.eventStreamRef,
      resultRef: firstRuntime.resultRef,
    },
    runtime: {
      run: { runId: run.runId, status: run.status, ownerType: run.ownerType },
      result: {
        status: result.status,
        ownerType: result.ownerType,
        latencyMs: result.latencyMs,
        retryable: result.retryable,
        usage: result.usage,
      },
      eventSources: [...new Set(events.list.map((event) => event.source))],
      streamFrame: { sequence: streamFrame.sequence, type: streamFrame.type, source: streamFrame.source },
      recoveryFrame: { sequence: recoveryFrame.sequence, type: recoveryFrame.type, source: recoveryFrame.source },
    },
    screenshot,
  }
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`)
  console.log(`PASS customer assistant chatflow runtime gateway UAT session=${first.sessionId} run=${firstRuntime.runId}`)
} finally {
  await browser.close()
}
