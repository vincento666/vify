import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const calls = []

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function envelope(data) {
  return { code: 200, message: 'success', data }
}

const turnResult = {
  runId: 46,
  sessionId: 120,
  replyType: 'DRAFT',
  operatorRecommendation: 'Operator recommendations:\\n- 已识别退票任务，请继续收集订单号。',
  customerReplyDraft: '请提供订单号，我会继续帮您办理退票。',
  taskSummaries: [
    {
      id: 501,
      sessionId: 120,
      taskKey: 'refund_ticket',
      taskType: 'refund',
      businessKey: 'refund_ticket',
      shortId: 'refund-501',
      status: 'WAITING',
      workerType: 'chatflow_sop',
      workerRef: 'flight_refund',
      checkpoint: { pendingPrompt: '请提供订单号' },
      lastResult: { missingFields: ['订单号'] },
      proposedActions: [],
      version: 1,
    },
  ],
  proposedActions: [],
  warnings: ['等待客户补充订单号。'],
  events: [
    {
      id: 9001,
      sessionId: 120,
      runId: 46,
      sequence: 1,
      type: 'run_started',
      visibility: 'normal',
      source: 'customer_assistant',
      actor: 'customer',
      payload: { message: '我要退票', actor: 'customer' },
      createdAt: '2026-06-14T04:40:00',
    },
  ],
  replayed: false,
}

const metricsResult = {
  sessionId: 120,
  taskStatusCounts: { WAITING: 1 },
  proposedActionStatusCounts: {},
  humanConfirmation: { pending: 0, adopted: 0, terminal: 0, adoptionRate: 0 },
  eventCounts: { total: 1, byType: { run_started: 1 }, bySource: { customer_assistant: 1 } },
  workerEventCounts: { total: 0, byType: {} },
  recentFailureReasons: [],
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.route('**/api/v1/customer-assistant/**', async (route) => {
    const request = route.request()
    const url = request.url()
    const method = request.method()
    calls.push({ method, url, body: request.postDataJSON?.() })

    if (method === 'POST' && url.endsWith('/sessions')) {
      await route.fulfill({ json: envelope({ id: 120, status: 'ACTIVE', context: {} }) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions/120/turns')) {
      await route.fulfill({ json: envelope(turnResult) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/120/tasks')) {
      await route.fulfill({ json: envelope({ list: turnResult.taskSummaries, total: 1 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/120/events')) {
      await route.fulfill({ json: envelope({ list: turnResult.events, total: 1 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/120/proposed-actions')) {
      await route.fulfill({ json: envelope({ list: turnResult.proposedActions, total: 0 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/120/metrics')) {
      await route.fulfill({ json: envelope(metricsResult) })
      return
    }
    await route.fulfill({ status: 404, json: { code: 404, message: 'missing route', data: null } })
  })

  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('button', { name: '模拟客户输入' }).click()
  await page
    .getByTestId('operator-recommendation-panel')
    .getByText('已识别退票任务，请继续收集订单号。')
    .waitFor({ state: 'visible', timeout: 10000 })

  assert(calls.some((call) => call.method === 'POST' && call.url.endsWith('/sessions')), 'Expected create session call')
  assert(calls.some((call) => call.method === 'POST' && call.url.endsWith('/sessions/120/turns')), 'Expected turn call')
  assert(calls.some((call) => call.method === 'GET' && call.url.endsWith('/sessions/120/tasks')), 'Expected task refresh')
  assert(calls.some((call) => call.method === 'GET' && call.url.endsWith('/sessions/120/events')), 'Expected event refresh')
  assert(calls.some((call) => call.method === 'GET' && call.url.endsWith('/sessions/120/proposed-actions')), 'Expected action refresh')
  assert(calls.some((call) => call.method === 'GET' && call.url.endsWith('/sessions/120/metrics')), 'Expected metrics refresh')

  const turnCall = calls.find((call) => call.method === 'POST' && call.url.endsWith('/sessions/120/turns'))
  assert(turnCall.body.message === '我要退票', `Expected message payload, got ${JSON.stringify(turnCall.body)}`)
  assert(turnCall.body.actor === 'customer', `Expected customer actor payload, got ${JSON.stringify(turnCall.body)}`)
  assert(turnCall.body.idempotencyKey, 'Expected idempotency key in turn payload')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant API integration e2e')
} finally {
  await browser.close()
}
