import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5174'
const artifactDir = process.env.HIFY_E2E_ARTIFACT_DIR || 'output/playwright/runtime-lab-sop-live-stream'
const screenshotPath = join(artifactDir, 'runtime-lab-sop-live-stream.png')
const reportPath = join(artifactDir, 'runtime-lab-sop-live-stream.json')

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function envelope(data) {
  return { code: 200, message: 'success', data }
}

function sse(frame) {
  return `data: ${JSON.stringify(frame)}\n\n`
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const streamCalls = []
let jsonFallbackCalls = 0

try {
  await mkdir(artifactDir, { recursive: true })
  await page.route('**/api/v1/runtime-lab/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (request.method() === 'POST' && url.pathname.endsWith('/sessions')) {
      await route.fulfill({ contentType: 'application/json', body: JSON.stringify(envelope({ id: 71 })) })
      return
    }
    if (request.method() === 'GET' && url.pathname.endsWith('/config')) {
      await route.fulfill({
        contentType: 'application/json',
        body: JSON.stringify(envelope({
          sopBindings: [],
          arbitrator: { mode: 'fake', model: 'mock', baseUrl: 'mock://runtime-lab', apiKeyConfigured: false, available: true },
          fallbackAgentOptions: [],
        })),
      })
      return
    }
    if (request.method() === 'POST' && url.pathname.endsWith('/messages:stream')) {
      streamCalls.push({ afterSequence: url.searchParams.get('afterSequence'), body: request.postDataJSON() })
      const initial = {
        type: 'delta', source: 'runtime_lab', sessionId: 71, runId: 42,
        payload: {
          reply: 'Chatflow SOP 正在后台执行，请稍候。',
          routeDecision: { action: 'START_SOP', targetSopId: 'refund_ticket' },
          activeTask: null, suspendedTasks: [], resumeOffer: null,
        },
      }
      const body = streamCalls.length === 1
        ? `${sse(initial)}${sse({ type: 'delta', source: 'provider', sessionId: 71, runId: 42, sequence: 4, delta: '正在核验' })}`
        : `${sse(initial)}${sse({
          type: 'done', source: 'runtime_v2', sessionId: 71, runId: 42, sequence: 5,
          event: { type: 'workflow_run_interrupted', payload: { output: { interrupt: { question: '请确认是否继续办理。' } } } },
        })}`
      await route.fulfill({ status: 200, contentType: 'text/event-stream', body })
      return
    }
    if (request.method() === 'POST' && url.pathname.endsWith('/messages')) {
      jsonFallbackCalls += 1
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify(envelope({})) })
      return
    }
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(envelope({ list: [], total: 0, tasks: [] })) })
  })
  await page.route('**/api/v1/agents/**', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(envelope([])) })
  })
  await page.route('**/api/v1/providers**', async (route) => {
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(envelope({ list: [], total: 0 })) })
  })

  await page.goto(`${baseUrl}/runtime-lab/chat`, { waitUntil: 'networkidle' })
  await page.getByTestId('runtime-lab-chat').waitFor({ timeout: 15_000 })
  await page.getByTestId('runtime-lab-input').fill('我要退票')
  await page.getByTestId('runtime-lab-send').click()
  await page.getByText('正在核验', { exact: false }).waitFor({ timeout: 15_000 })
  await page.getByText('请确认是否继续办理。', { exact: false }).waitFor({ timeout: 15_000 })

  assert(streamCalls.length === 2, `expected stream reconnect, got ${JSON.stringify(streamCalls)}`)
  assert(streamCalls[0].afterSequence === '0', `expected initial cursor 0: ${JSON.stringify(streamCalls)}`)
  assert(streamCalls[1].afterSequence === '4', `expected reconnect cursor 4: ${JSON.stringify(streamCalls)}`)
  assert(streamCalls.every((call) => call.body.idempotencyKey === streamCalls[0].body.idempotencyKey), 'expected stable idempotency key')
  assert(jsonFallbackCalls === 0, 'JSON fallback must not run when SSE reconnect succeeds')

  await page.screenshot({ path: screenshotPath, fullPage: true })
  await writeFile(reportPath, `${JSON.stringify({ streamCalls, jsonFallbackCalls, screenshotPath }, null, 2)}\n`)
  console.log(`PASS RuntimeLab SOP live stream UI UAT ${screenshotPath}`)
} finally {
  await browser.close()
}
