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

const failedTask = {
  id: 201,
  sessionId: 22,
  taskKey: 'refund_ticket:timeout',
  taskType: 'refund',
  businessKey: 'refund_ticket',
  shortId: 'refund-201',
  status: 'FAILED',
  workerType: 'react_worker',
  workerRef: 'refund_retry_agent',
  checkpoint: { currentStep: 'tool_call' },
  lastResult: {
    status: 'FAILED',
    error: '工具调用超时 [REDACTED] api_key=***',
  },
  proposedActions: [],
  version: 3,
}

const retryAction = {
  id: 77,
  sessionId: 22,
  runId: 44,
  taskId: 201,
  actionKey: 'refund_ticket:timeout:retry',
  actionType: 'PROPOSED_TASK_COMMAND',
  title: '重试任务：refund_ticket:timeout',
  payload: {
    controlType: 'retry',
    reason: 'operator retry requested from workbench',
    taskCommand: { type: 'RETRY_TASK', taskKey: 'refund_ticket:timeout', taskId: 201 },
  },
  status: 'PENDING',
}

const turnResult = {
  runId: 44,
  sessionId: 22,
  replyType: 'DRAFT',
  operatorRecommendation: 'Operator recommendations:\n- 退票工具调用失败，请先生成重试任务控制。',
  customerReplyDraft: '退票工具暂时不可用，我会继续为您处理。',
  taskSummaries: [failedTask],
  proposedActions: [],
  warnings: ['工具调用失败，等待坐席确认是否重试。'],
  events: [
    {
      id: 900,
      sessionId: 22,
      runId: 44,
      sequence: 1,
      type: 'worker_failed',
      visibility: 'operator',
      source: 'react_worker',
      taskId: 201,
      payload: { reason: '工具调用超时 [REDACTED] api_key=***' },
    },
  ],
  replayed: false,
}

const initialMetrics = {
  sessionId: 22,
  taskStatusCounts: { FAILED: 1 },
  proposedActionStatusCounts: {},
  humanConfirmation: { pending: 0, adopted: 0, terminal: 0, adoptionRate: 0 },
  eventCounts: { total: 1, byType: { worker_failed: 1 }, bySource: { react_worker: 1 } },
  workerEventCounts: { total: 1, byType: { worker_failed: 1 } },
  recentFailureReasons: [
    { taskId: 201, taskType: 'refund', source: 'react_worker', reason: '工具调用超时 [REDACTED] api_key=***' },
  ],
}

const retryMetrics = {
  ...initialMetrics,
  proposedActionStatusCounts: { PENDING: 1 },
  humanConfirmation: { pending: 1, adopted: 0, terminal: 0, adoptionRate: 0 },
}

let retryProposed = false

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
    if (method === 'GET' && url.endsWith('/worker-profiles')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions')) {
      await route.fulfill({ json: envelope({ id: 22, status: 'ACTIVE', context: {} }) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions/22/turns')) {
      await route.fulfill({ json: envelope(turnResult) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions/22/tasks/201/controls/propose')) {
      const body = request.postDataJSON?.()
      assert(body.controlType === 'retry', `Expected retry proposal body, got ${JSON.stringify(body)}`)
      assert(
        body.reason === 'operator retry requested from workbench',
        `Expected workbench retry reason, got ${JSON.stringify(body)}`,
      )
      retryProposed = true
      await route.fulfill({ json: envelope(retryAction) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/22/tasks')) {
      await route.fulfill({ json: envelope({ list: [failedTask], total: 1 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/22/events')) {
      const retryEvent = {
        id: 901,
        sessionId: 22,
        runId: 44,
        sequence: 2,
        type: 'task_control_proposed',
        visibility: 'operator',
        source: 'operator_advisory',
        taskId: 201,
        payload: { actionId: retryAction.id, controlType: 'retry' },
      }
      await route.fulfill({
        json: envelope({
          list: retryProposed ? [...turnResult.events, retryEvent] : turnResult.events,
          total: retryProposed ? 2 : 1,
        }),
      })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/22/proposed-actions')) {
      await route.fulfill({
        json: envelope({ list: retryProposed ? [retryAction] : [], total: retryProposed ? 1 : 0 }),
      })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/22/metrics')) {
      await route.fulfill({ json: envelope(retryProposed ? retryMetrics : initialMetrics) })
      return
    }
    await route.fulfill({ status: 404, json: { code: 404, message: 'unexpected call', data: null } })
  })

  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('button', { name: '模拟客户输入' }).click()

  const taskLedger = page.getByTestId('operator-task-ledger')
  const failedTaskRow = taskLedger.locator('.task-row').filter({ hasText: 'refund_ticket:timeout' })
  await failedTaskRow.getByText('FAILED').waitFor({ state: 'visible', timeout: 10000 })
  await failedTaskRow.getByRole('button', { name: '重试' }).click()

  await page.getByTestId('operator-proposed-actions-panel').getByText('重试任务：refund_ticket:timeout').waitFor({
    state: 'visible',
    timeout: 10000,
  })
  await page.getByTestId('operator-proposed-actions-panel').getByText('PENDING').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('operator-metrics-panel').getByText('待确认动作').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('operator-metrics-panel').getByText('工具调用超时 [REDACTED] api_key=***').waitFor({
    state: 'visible',
    timeout: 10000,
  })

  const retryCalls = calls.filter((call) => call.method === 'POST' && call.url.endsWith('/sessions/22/tasks/201/controls/propose'))
  assert(retryCalls.length === 1, `Expected one retry proposal API call, got ${retryCalls.length}`)
  assert(retryCalls[0].body.controlType === 'retry', `Expected retry control type, got ${JSON.stringify(retryCalls[0].body)}`)
  assert(
    retryCalls[0].body.reason === 'operator retry requested from workbench',
    `Expected workbench retry reason, got ${JSON.stringify(retryCalls[0].body)}`,
  )

  const customerLaneText = await page.getByTestId('customer-conversation-lane').innerText()
  assert(!customerLaneText.includes('重试'), 'Customer lane must not expose failed-task retry controls')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant retry recovery e2e')
} finally {
  await browser.close()
}
