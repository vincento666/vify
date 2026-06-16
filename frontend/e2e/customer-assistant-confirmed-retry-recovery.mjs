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
  sessionId: 32,
  taskKey: 'baggage_qa:recoverable',
  taskType: 'QA',
  businessKey: 'baggage_allowance',
  shortId: 'recoverable-201',
  status: 'FAILED',
  workerType: 'stub_qa',
  workerRef: 'baggage_allowance',
  checkpoint: { topic: 'baggage_allowance' },
  lastResult: { status: 'FAILED', error: { code: 'WORKER_FAILED', message: 'previous deterministic failure' } },
  proposedActions: [],
  version: 4,
}

const completedTask = {
  ...failedTask,
  status: 'COMPLETED',
  lastResult: {
    status: 'COMPLETED',
    operatorRecommendation: '行李额重试已恢复，建议告知旅客手提行李和托运行李额度。',
    customerReplyDraft: '您的手提行李额度已恢复查询，可携带 1 件手提行李。',
  },
  workerAsyncRefs: {
    supported: true,
    workerRunId: 'customer-assistant-worker-run-201-2',
    workerStatusRef: '/api/v1/customer-assistant/worker-runs/customer-assistant-worker-run-201-2',
    workerEventsRef: '/api/v1/customer-assistant/worker-runs/customer-assistant-worker-run-201-2/events',
    workerResultRef: '/api/v1/customer-assistant/worker-runs/customer-assistant-worker-run-201-2/result',
  },
}

const retryAction = {
  id: 77,
  sessionId: 32,
  runId: 55,
  taskId: 201,
  actionKey: 'baggage_qa:recoverable:retry',
  actionType: 'PROPOSED_TASK_COMMAND',
  title: '重试任务：baggage_qa:recoverable',
  payload: {
    controlType: 'retry',
    reason: 'operator retry requested from workbench',
    taskCommand: { type: 'RESUME_TASK', taskKey: 'baggage_qa:recoverable', taskId: 201 },
  },
  status: 'PENDING',
}

const confirmedRetryAction = {
  ...retryAction,
  status: 'CONFIRMED',
  result: {
    applied: true,
    taskCommand: retryAction.payload.taskCommand,
    workerResultCount: 1,
    updatedTaskIds: [201],
    workerRunIds: ['customer-assistant-worker-run-201-2'],
  },
}

const baseEvents = [
  {
    id: 910,
    sessionId: 32,
    runId: 55,
    sequence: 1,
    type: 'worker_failed',
    visibility: 'operator',
    source: 'stub_qa',
    taskId: 201,
    payload: { reason: 'previous deterministic failure' },
  },
]

const retryEvents = [
  ...baseEvents,
  {
    id: 911,
    sessionId: 32,
    runId: 55,
    sequence: 2,
    type: 'task_control_proposed',
    visibility: 'operator',
    source: 'operator_advisory',
    taskId: 201,
    payload: { actionId: 77, controlType: 'retry' },
  },
]

const confirmedEvents = [
  ...retryEvents,
  {
    id: 912,
    sessionId: 32,
    runId: 55,
    sequence: 3,
    type: 'proposed_task_command_confirmed',
    visibility: 'operator',
    source: 'operator_advisory',
    taskId: 201,
    payload: { actionId: 77, taskCommand: retryAction.payload.taskCommand },
  },
  {
    id: 913,
    sessionId: 32,
    runId: 55,
    sequence: 4,
    type: 'task_started',
    visibility: 'operator',
    source: 'worker',
    taskId: 201,
    payload: { taskKey: failedTask.taskKey, workerType: 'stub_qa' },
  },
  {
    id: 914,
    sessionId: 32,
    runId: 55,
    sequence: 5,
    type: 'worker_started',
    visibility: 'operator',
    source: 'worker',
    taskId: 201,
    payload: { workerRunId: 'customer-assistant-worker-run-201-2' },
  },
  {
    id: 915,
    sessionId: 32,
    runId: 55,
    sequence: 6,
    type: 'task_completed',
    visibility: 'operator',
    source: 'worker',
    taskId: 201,
    payload: { workerRunId: 'customer-assistant-worker-run-201-2' },
  },
]

const turnResult = {
  runId: 55,
  sessionId: 32,
  replyType: 'DRAFT',
  operatorRecommendation: 'Operator recommendations:\n- 行李额任务失败，可由坐席确认重试。',
  customerReplyDraft: '行李额查询暂时失败，我会继续为您处理。',
  taskSummaries: [failedTask],
  proposedActions: [],
  warnings: ['任务失败，等待坐席确认重试。'],
  events: baseEvents,
  replayed: false,
}

const failedMetrics = {
  sessionId: 32,
  taskStatusCounts: { FAILED: 1 },
  proposedActionStatusCounts: {},
  humanConfirmation: { pending: 0, adopted: 0, terminal: 0, adoptionRate: 0 },
  eventCounts: { total: 1, byType: { worker_failed: 1 }, bySource: { stub_qa: 1 } },
  workerEventCounts: { total: 1, byType: { worker_failed: 1 } },
  recentFailureReasons: [{ taskId: 201, taskType: 'QA', source: 'stub_qa', reason: 'previous deterministic failure' }],
}

const retryMetrics = {
  ...failedMetrics,
  proposedActionStatusCounts: { PENDING: 1 },
  humanConfirmation: { pending: 1, adopted: 0, terminal: 0, adoptionRate: 0 },
}

const recoveredMetrics = {
  sessionId: 32,
  taskStatusCounts: { COMPLETED: 1 },
  proposedActionStatusCounts: { CONFIRMED: 1 },
  humanConfirmation: { pending: 0, adopted: 1, terminal: 1, adoptionRate: 1 },
  eventCounts: {
    total: 6,
    byType: {
      worker_failed: 1,
      task_control_proposed: 1,
      proposed_task_command_confirmed: 1,
      task_started: 1,
      worker_started: 1,
      task_completed: 1,
    },
    bySource: { stub_qa: 1, operator_advisory: 2, worker: 3 },
  },
  workerEventCounts: { total: 3, byType: { task_started: 1, worker_started: 1, task_completed: 1 } },
  recentFailureReasons: [],
}

let retryProposed = false
let retryConfirmed = false

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
      await route.fulfill({ json: envelope({ id: 32, status: 'ACTIVE', context: {} }) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions/32/turns')) {
      await route.fulfill({ json: envelope(turnResult) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions/32/tasks/201/controls/propose')) {
      const body = request.postDataJSON?.()
      assert(body.controlType === 'retry', `Expected retry proposal body, got ${JSON.stringify(body)}`)
      retryProposed = true
      await route.fulfill({ json: envelope(retryAction) })
      return
    }
    if (method === 'POST' && url.endsWith('/proposed-actions/77/confirm')) {
      retryConfirmed = true
      await route.fulfill({ json: envelope(confirmedRetryAction) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/32/tasks')) {
      await route.fulfill({ json: envelope({ list: [retryConfirmed ? completedTask : failedTask], total: 1 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/32/events')) {
      const events = retryConfirmed ? confirmedEvents : retryProposed ? retryEvents : baseEvents
      await route.fulfill({ json: envelope({ list: events, total: events.length }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/32/proposed-actions')) {
      const actions = retryConfirmed ? [confirmedRetryAction] : retryProposed ? [retryAction] : []
      await route.fulfill({ json: envelope({ list: actions, total: actions.length }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/32/metrics')) {
      await route.fulfill({ json: envelope(retryConfirmed ? recoveredMetrics : retryProposed ? retryMetrics : failedMetrics) })
      return
    }
    await route.fulfill({ status: 404, json: { code: 404, message: 'unexpected call', data: null } })
  })

  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('button', { name: '模拟客户输入' }).click()

  const taskLedger = page.getByTestId('operator-task-ledger')
  const taskRow = taskLedger.locator('.task-row').filter({ hasText: 'baggage_qa:recoverable' })
  await taskRow.getByText('FAILED').waitFor({ state: 'visible', timeout: 10000 })
  await taskRow.getByRole('button', { name: '重试' }).click()

  const actionPanel = page.getByTestId('operator-proposed-actions-panel')
  const retryActionRow = actionPanel.locator('.action-row').filter({ hasText: '重试任务：baggage_qa:recoverable' })
  await retryActionRow.getByText('PENDING').waitFor({ state: 'visible', timeout: 10000 })
  await retryActionRow.getByLabel('确认拟议动作').click()

  await taskRow.getByText('COMPLETED').waitFor({ state: 'visible', timeout: 10000 })
  await retryActionRow.getByText('CONFIRMED').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('operator-event-timeline').getByText('task_completed').waitFor({
    state: 'visible',
    timeout: 10000,
  })

  const retryCalls = calls.filter((call) => call.method === 'POST' && call.url.endsWith('/sessions/32/tasks/201/controls/propose'))
  assert(retryCalls.length === 1, `Expected one retry proposal call, got ${retryCalls.length}`)
  const confirmCalls = calls.filter((call) => call.method === 'POST' && call.url.endsWith('/proposed-actions/77/confirm'))
  assert(confirmCalls.length === 1, `Expected one task-command confirm call, got ${confirmCalls.length}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant confirmed retry recovery e2e')
} finally {
  await browser.close()
}
