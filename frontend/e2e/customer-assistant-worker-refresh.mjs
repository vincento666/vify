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

const pendingTask = {
  id: 301,
  sessionId: 41,
  taskKey: 'refund_ticket:async',
  taskType: 'REFUND',
  businessKey: 'order-2026-redacted',
  shortId: 'refund-301',
  status: 'RUNNING',
  workerType: 'react_worker',
  workerRef: 'refund_async_worker',
  checkpoint: { orderNo: 'HF***2026' },
  lastResult: {
    status: 'PENDING',
    workerAsyncRefs: {
      supported: true,
      workerRunId: 'worker-run-301',
      workerStatusRef: '/api/v1/customer-assistant/worker-runs/worker-run-301',
      workerEventsRef: '/api/v1/customer-assistant/worker-runs/worker-run-301/events',
      workerEventStreamRef: '/api/v1/customer-assistant/worker-runs/worker-run-301/events/stream',
      workerResultRef: '/api/v1/customer-assistant/worker-runs/worker-run-301/result',
    },
  },
  proposedActions: [],
  version: 1,
}

const completedTask = {
  ...pendingTask,
  status: 'COMPLETED',
  lastResult: {
    ...pendingTask.lastResult,
    status: 'COMPLETED',
    operatorRecommendation: '异步退票 Worker 已完成，建议坐席核对手续费后确认。',
    customerReplyDraft: '您的退票申请已完成核验，稍后由坐席确认手续费。',
  },
}

const baseEvents = [
  {
    id: 940,
    sessionId: 41,
    runId: 71,
    sequence: 1,
    type: 'worker_started',
    visibility: 'operator',
    source: 'react_worker',
    taskId: 301,
    payload: { taskKey: pendingTask.taskKey, workerRunId: 'worker-run-301' },
  },
]

const completedEvents = [
  ...baseEvents,
  {
    id: 941,
    sessionId: 41,
    runId: 71,
    sequence: 2,
    type: 'task_completed',
    visibility: 'operator',
    source: 'react_worker',
    taskId: 301,
    payload: { taskKey: pendingTask.taskKey, workerRunId: 'worker-run-301' },
  },
]

const cancelledEvents = [
  ...baseEvents,
  {
    id: 941,
    sessionId: 41,
    runId: 71,
    sequence: 2,
    type: 'worker_cancel_requested',
    visibility: 'operator',
    source: 'customer_assistant_worker',
    taskId: 301,
    payload: { workerRunId: 'worker-run-301', supported: false },
  },
  {
    id: 942,
    sessionId: 41,
    runId: 71,
    sequence: 3,
    type: 'worker_cancel_unsupported',
    visibility: 'operator',
    source: 'customer_assistant_worker',
    taskId: 301,
    payload: { workerRunId: 'worker-run-301', supported: false },
  },
]

const turnResult = {
  runId: 71,
  sessionId: 41,
  replyType: 'DRAFT',
  operatorRecommendation: '异步退票任务正在执行，可稍后刷新 Worker 结果。',
  customerReplyDraft: '我正在为您核验退票信息，请稍等。',
  taskSummaries: [pendingTask],
  proposedActions: [],
  warnings: [],
  events: baseEvents,
  replayed: false,
}

const pendingMetrics = {
  sessionId: 41,
  taskStatusCounts: { RUNNING: 1 },
  proposedActionStatusCounts: {},
  humanConfirmation: { pending: 0, adopted: 0, terminal: 0, adoptionRate: 0 },
  eventCounts: { total: 1, byType: { worker_started: 1 }, bySource: { react_worker: 1 } },
  workerEventCounts: { total: 1, byType: { worker_started: 1 } },
  recentFailureReasons: [],
}

const completedMetrics = {
  ...pendingMetrics,
  taskStatusCounts: { COMPLETED: 1 },
  eventCounts: {
    total: 2,
    byType: { worker_started: 1, task_completed: 1 },
    bySource: { react_worker: 2 },
  },
  workerEventCounts: { total: 2, byType: { worker_started: 1, task_completed: 1 } },
}

let refreshed = false
let cancelled = false

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })

try {
  await page.route('**/api/v1/customer-assistant/**', async (route) => {
    const request = route.request()
    const url = request.url()
    const method = request.method()
    calls.push({ method, url, body: request.postDataJSON?.() })

    if (method === 'GET' && url.endsWith('/demo-stories')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/demo-stories/metrics')) {
      await route.fulfill({ json: envelope(completedMetrics) })
      return
    }
    if (method === 'GET' && url.endsWith('/worker-profiles')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions')) {
      await route.fulfill({ json: envelope({ id: 41, status: 'ACTIVE', context: {} }) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions/41/turns')) {
      await route.fulfill({ json: envelope(turnResult) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions/41/worker-results/refresh')) {
      refreshed = true
      await route.fulfill({ json: envelope({ consumed: 1 }) })
      return
    }
    if (method === 'POST' && url.endsWith('/worker-runs/worker-run-301/cancel')) {
      cancelled = true
      await route.fulfill({
        json: envelope({
          workerRunId: 'worker-run-301',
          status: 'cancel_unsupported',
          cancellation: {
            supported: false,
            reason: 'Cooperative cancellation is not supported for this customer-assistant worker.',
          },
        }),
      })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/41/tasks')) {
      await route.fulfill({ json: envelope({ list: [refreshed ? completedTask : pendingTask], total: 1 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/41/events')) {
      const events = refreshed ? completedEvents : cancelled ? cancelledEvents : baseEvents
      await route.fulfill({ json: envelope({ list: events, total: events.length }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/41/proposed-actions')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/41/metrics')) {
      await route.fulfill({ json: envelope(refreshed ? completedMetrics : pendingMetrics) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/41/operator-audit')) {
      await route.fulfill({ json: envelope({ sessionId: 41, list: [], total: 0 }) })
      return
    }
    await route.fulfill({ status: 404, json: { code: 404, message: 'unexpected call', data: null } })
  })

  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('button', { name: '模拟客户输入' }).click()

  const taskLedger = page.getByTestId('operator-task-ledger')
  const taskRow = taskLedger.locator('.task-row').filter({ hasText: 'refund_ticket:async' })
  await taskRow.getByText('RUNNING').waitFor({ state: 'visible', timeout: 10000 })
  await taskRow.getByTestId('operator-worker-async-refs').getByText('Run worker-run-301').waitFor({
    state: 'visible',
    timeout: 10000,
  })
  await taskRow.getByRole('button', { name: '请求取消' }).click()
  await page.getByTestId('operator-event-timeline').getByText('worker_cancel_unsupported').waitFor({
    state: 'visible',
    timeout: 10000,
  })
  await taskRow.getByRole('button', { name: '刷新结果' }).click()
  await taskRow.getByText('COMPLETED').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('operator-event-timeline').getByText('task_completed').waitFor({
    state: 'visible',
    timeout: 10000,
  })

  const refreshCalls = calls.filter((call) => (
    call.method === 'POST' && call.url.endsWith('/sessions/41/worker-results/refresh')
  ))
  assert(refreshCalls.length === 1, `Expected one worker refresh call, got ${refreshCalls.length}`)
  const cancelCalls = calls.filter((call) => (
    call.method === 'POST' && call.url.endsWith('/worker-runs/worker-run-301/cancel')
  ))
  assert(cancelCalls.length === 1, `Expected one worker cancel call, got ${cancelCalls.length}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant worker refresh e2e')
} finally {
  await browser.close()
}
