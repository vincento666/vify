import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const artifactDir = process.env.HIFY_E2E_ARTIFACT_DIR
  || '/Users/vincento/work/develop/hify/artifacts/slices/207-final-uat-gates/207.1'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || join(artifactDir, 'screenshots')
const reportPath = process.env.HIFY_E2E_REPORT || join(artifactDir, 'unified-routing-sop-chatflow-runtime-uat.json')

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

async function getJson(page, path, label) {
  return unwrap(await page.request.get(`${baseUrl}${path}`), label)
}

async function getSseFrame(page, path, label) {
  const response = await page.request.get(`${baseUrl}${path}`, {
    headers: { Accept: 'text/event-stream' },
  })
  const text = await response.text()
  assert(response.ok(), `${label} HTTP ${response.status()}: ${text}`)
  const dataLine = text.split('\n').find((line) => line.startsWith('data:'))
  assert(dataLine, `${label} should return an SSE data frame: ${text}`)
  return JSON.parse(dataLine.slice('data:'.length).trim())
}

async function sendTurn(page, message) {
  await page.getByTestId('runtime-lab-input').fill(message)
  await page.getByTestId('runtime-lab-send').click()
}

async function waitForRouteAction(page, action) {
  await page.getByTestId('route-action').filter({ hasText: action }).waitFor({ timeout: 45_000 })
}

async function currentSessionId(page) {
  const label = await page.locator('.session-id').innerText({ timeout: 15_000 })
  const id = Number(label.replace(/[^0-9]/g, ''))
  assert(Number.isInteger(id) && id > 0, `expected runtime lab session id, got ${label}`)
  return id
}

async function expectTaskStatus(page, sopId, status) {
  await page.locator('.task-row').filter({ hasText: sopId }).filter({ hasText: status }).last().waitFor({
    timeout: 45_000,
  })
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await mkdir(screenshotDir, { recursive: true })
  await page.goto(`${baseUrl}/runtime-lab/chat`, { waitUntil: 'networkidle' })
  await page.getByTestId('runtime-lab-chat').waitFor({ timeout: 15_000 })

  await sendTurn(page, '我要退票')
  await waitForRouteAction(page, 'START_SOP')

  await sendTurn(page, '订单号 TK207，手机号 13800138000，乘机人张测试')
  await waitForRouteAction(page, 'CONTINUE_ACTIVE_SOP')

  await sendTurn(page, '确认')
  await waitForRouteAction(page, 'COMPLETE_TASK')
  await expectTaskStatus(page, 'refund_ticket', 'COMPLETED')
  await page.getByTestId('chatflow-trace-panel').filter({ hasText: 'refund_ticket' }).waitFor({ timeout: 15_000 })

  const sessionId = await currentSessionId(page)
  const trace = await getJson(page, `/api/v1/runtime-lab/sessions/${sessionId}/chatflow-trace`, 'get chatflow trace')
  const task = trace.tasks.find((item) => item.sopId === 'refund_ticket')
  assert(task, `refund_ticket trace should exist: ${JSON.stringify(trace)}`)
  assert(task.status === 'COMPLETED', `refund_ticket task should complete: ${JSON.stringify(task)}`)
  assert(task.chatflow?.runId > 0, `trace should expose runtime run id: ${JSON.stringify(task)}`)
  assert(task.chatflow.runtimeVersion === 2 || task.chatflow.eventStreamRef, `trace should expose runtime refs: ${JSON.stringify(task)}`)

  const run = await getJson(page, task.chatflow.statusRef, 'get runtime run')
  const result = await getJson(page, task.chatflow.resultRef, 'get runtime result')
  const events = await getJson(page, task.chatflow.eventsRef, 'get runtime events')
  const streamFrame = await getSseFrame(
    page,
    withParam(task.chatflow.eventStreamRef, '_testLimit', '1'),
    'get runtime event stream',
  )

  assert(run.ownerType === 'CHATFLOW', `runtime run should be chatflow-owned: ${JSON.stringify(run)}`)
  assert(run.status === 'SUCCEEDED', `runtime run should succeed: ${JSON.stringify(run)}`)
  assert(result.ownerType === 'CHATFLOW', `runtime result should be chatflow-owned: ${JSON.stringify(result)}`)
  assert(result.status === 'SUCCEEDED', `runtime result should succeed: ${JSON.stringify(result)}`)
  assert(result.retryable === false, `runtime result should be non-retryable: ${JSON.stringify(result)}`)
  assert(Number.isInteger(result.latencyMs) && result.latencyMs >= 0, `runtime result should expose latency: ${JSON.stringify(result)}`)
  assert(events.list.some((event) => event.source === 'chatflow_runtime_v2'), `runtime events should be v2: ${JSON.stringify(events)}`)
  assert(streamFrame.source === 'chatflow_runtime_v2', `SSE frame should be v2: ${JSON.stringify(streamFrame)}`)

  const screenshot = join(screenshotDir, 'unified-routing-sop-chatflow-runtime.png')
  await page.screenshot({ path: screenshot, fullPage: true })
  const report = {
    sessionId,
    routeAction: await page.getByTestId('route-action').innerText(),
    trace: {
      taskId: task.taskId,
      sopId: task.sopId,
      status: task.status,
      runId: task.chatflow.runId,
      statusRef: task.chatflow.statusRef,
      eventsRef: task.chatflow.eventsRef,
      eventStreamRef: task.chatflow.eventStreamRef,
      resultRef: task.chatflow.resultRef,
    },
    run: {
      runId: run.runId,
      status: run.status,
      ownerType: run.ownerType,
    },
    result: {
      status: result.status,
      ownerType: result.ownerType,
      latencyMs: result.latencyMs,
      retryable: result.retryable,
      usage: result.usage,
    },
    eventSources: [...new Set(events.list.map((event) => event.source))],
    streamFrame: {
      sequence: streamFrame.sequence,
      type: streamFrame.type,
      source: streamFrame.source,
    },
    screenshot,
  }
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`)
  console.log(`PASS unified routing SOP chatflow runtime UAT session=${sessionId} run=${task.chatflow.runId}`)
} finally {
  await browser.close()
}
