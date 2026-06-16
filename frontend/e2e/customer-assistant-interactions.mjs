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

const confirmedAction = {
  id: 9,
  sessionId: 12,
  runId: 31,
  taskId: 101,
  actionKey: 'refund_ticket:submit_refund:TK-100',
  actionType: 'submit_refund',
  title: '提交退票申请',
  payload: { orderNo: 'TK-100' },
  status: 'CONFIRMED',
}

const pendingAction = {
  ...confirmedAction,
  status: 'PENDING',
}

const turnResult = {
  runId: 31,
  sessionId: 12,
  replyType: 'DRAFT',
  operatorRecommendation: 'Operator recommendations:\n- 已识别退票任务，请继续确认订单。',
  customerReplyDraft: '已为您查询订单 TK-100，请确认是否提交退票申请。',
  taskSummaries: [
    {
      id: 101,
      sessionId: 12,
      taskKey: 'refund_ticket',
      taskType: 'refund',
      businessKey: 'refund_ticket',
      shortId: 'refund-101',
      status: 'COMPLETED',
      workerType: 'chatflow_sop',
      workerRef: 'refund_ticket',
      checkpoint: { currentStep: 'completed' },
      lastResult: { status: 'COMPLETED' },
      proposedActions: [pendingAction],
      version: 1,
    },
  ],
  proposedActions: [pendingAction],
  warnings: [],
  events: [],
  replayed: false,
}

const pendingMetrics = {
  sessionId: 12,
  taskStatusCounts: { COMPLETED: 1 },
  proposedActionStatusCounts: { PENDING: 1 },
  humanConfirmation: { pending: 1, adopted: 0, terminal: 0, adoptionRate: 0 },
  eventCounts: { total: 0, byType: {}, bySource: {} },
  workerEventCounts: { total: 0, byType: {} },
  recentFailureReasons: [],
}

const confirmedMetrics = {
  ...pendingMetrics,
  proposedActionStatusCounts: { CONFIRMED: 1 },
  humanConfirmation: { pending: 0, adopted: 1, terminal: 1, adoptionRate: 1 },
}

let actionConfirmed = false

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.route('**/api/v1/customer-assistant/**', async (route) => {
    const request = route.request()
    const url = request.url()
    const method = request.method()
    calls.push({ method, url, body: request.postDataJSON?.() })

    if (method === 'POST' && url.endsWith('/proposed-actions/9/confirm')) {
      actionConfirmed = true
      await route.fulfill({ json: envelope(confirmedAction) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions')) {
      await route.fulfill({ json: envelope({ id: 12, status: 'ACTIVE', context: {} }) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions/12/turns')) {
      await route.fulfill({ json: envelope(turnResult) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/12/tasks')) {
      await route.fulfill({ json: envelope({ list: turnResult.taskSummaries, total: 1 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/12/events')) {
      await route.fulfill({ json: envelope({ list: turnResult.events, total: 0 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/12/proposed-actions')) {
      await route.fulfill({ json: envelope({ list: [pendingAction], total: 1 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/12/metrics')) {
      await route.fulfill({ json: envelope(actionConfirmed ? confirmedMetrics : pendingMetrics) })
      return
    }
    await route.fulfill({ status: 404, json: { code: 404, message: 'unexpected call', data: null } })
  })

  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('button', { name: '模拟客户输入' }).click()
  await page.getByTestId('operator-draft-panel').getByText('TK-100').waitFor({ state: 'visible', timeout: 10000 })
  const callsAfterTurn = calls.length

  await page.getByLabel('本地应用客户回复草稿').click()
  await page.getByTestId('operator-draft-panel').getByText('已本地应用').waitFor({
    state: 'visible',
    timeout: 10000,
  })
  assert(
    calls.length === callsAfterTurn,
    `Local draft apply must not call API, got ${JSON.stringify(calls.slice(callsAfterTurn))}`,
  )

  await page.getByLabel('确认拟议动作').click()
  await page.getByText('CONFIRMED').waitFor({ state: 'visible', timeout: 10000 })
  assert(await page.getByLabel('确认拟议动作').isDisabled(), 'Confirmed action should disable confirm control')
  assert(
    calls.some((call) => call.method === 'POST' && call.url.endsWith('/proposed-actions/9/confirm')),
    'Expected confirm action API call',
  )

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant interactions e2e')
} finally {
  await browser.close()
}
