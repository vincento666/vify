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

const confirmAction = {
  id: 9,
  sessionId: 12,
  runId: 31,
  taskId: 101,
  actionKey: 'refund_ticket:submit_refund:TK-100',
  actionType: 'submit_refund',
  title: '提交退票申请',
  payload: { orderNo: 'TK-100' },
  status: 'PENDING',
}

const rejectAction = {
  ...confirmAction,
  id: 10,
  actionKey: 'refund_ticket:manual_reject:TK-100',
  title: '拒绝退票申请',
}

let confirmStatus = 'PENDING'
let rejectStatus = 'PENDING'

function visibleActions() {
  return [
    { ...confirmAction, status: confirmStatus },
    { ...rejectAction, status: rejectStatus },
  ]
}

function turnResult() {
  return {
    runId: 31,
    sessionId: 12,
    replyType: 'DRAFT',
    operatorRecommendation: '请复核退票动作。',
    customerReplyDraft: '请确认是否继续办理退票。',
    taskSummaries: [],
    proposedActions: visibleActions(),
    warnings: [],
    events: [],
    replayed: false,
  }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.route('**/api/v1/customer-assistant/**', async (route) => {
    const request = route.request()
    const url = request.url()
    const method = request.method()
    const body = request.postDataJSON?.()
    calls.push({ method, url, body })

    if (method === 'POST' && url.endsWith('/proposed-actions/9/confirm')) {
      confirmStatus = 'CONFIRMED'
      await route.fulfill({ json: envelope({ ...confirmAction, status: confirmStatus, result: { decision: body } }) })
      return
    }
    if (method === 'POST' && url.endsWith('/proposed-actions/10/reject')) {
      rejectStatus = 'REJECTED'
      await route.fulfill({ json: envelope({ ...rejectAction, status: rejectStatus, result: { decision: body } }) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions')) {
      await route.fulfill({ json: envelope({ id: 12, status: 'ACTIVE', context: {} }) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions/12/turns')) {
      await route.fulfill({ json: envelope(turnResult()) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/12/tasks')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/12/events')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/12/proposed-actions')) {
      await route.fulfill({ json: envelope({ list: visibleActions(), total: 2 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/12/operator-audit')) {
      await route.fulfill({ json: envelope({ sessionId: 12, list: [], total: 0 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/12/metrics')) {
      await route.fulfill({
        json: envelope({
          sessionId: 12,
          taskStatusCounts: {},
          proposedActionStatusCounts: { [confirmStatus]: 1, [rejectStatus]: 1 },
          humanConfirmation: { pending: 0, adopted: 1, terminal: 2, adoptionRate: 0.5 },
          eventCounts: { total: 0, byType: {}, bySource: {} },
          workerEventCounts: { total: 0, byType: {} },
          recentFailureReasons: [],
        }),
      })
      return
    }
    if (method === 'GET' && url.endsWith('/demo-stories')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/demo-stories/metrics')) {
      await route.fulfill({
        json: envelope({
          storyCount: 0,
          sessionCount: 0,
          taskStatusCounts: {},
          proposedActionStatusCounts: {},
          humanConfirmation: { pending: 0, adopted: 0, terminal: 0, adoptionRate: 0 },
          eventCounts: { total: 0, byType: {}, bySource: {} },
          workerEventCounts: { total: 0, byType: {} },
          recentFailureReasons: [],
          stories: [],
        }),
      })
      return
    }
    if (method === 'GET' && url.endsWith('/worker-profiles')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
      return
    }
    await route.fulfill({ status: 404, json: { code: 404, message: 'unexpected call', data: null } })
  })

  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('button', { name: '模拟客户输入' }).click()

  const confirmRow = page.getByTestId('operator-proposed-actions-panel').locator('.action-row').filter({ hasText: '#9' })
  await confirmRow.getByLabel('确认备注').fill('客户已电话确认退票')
  await confirmRow.getByLabel('确认拟议动作').click()

  const rejectRow = page.getByTestId('operator-proposed-actions-panel').locator('.action-row').filter({ hasText: '#10' })
  await rejectRow.getByLabel('拒绝原因').fill('客户撤销退票申请')
  await rejectRow.getByLabel('拒绝拟议动作').click()

  const confirmCall = calls.find((call) => call.method === 'POST' && call.url.endsWith('/proposed-actions/9/confirm'))
  const rejectCall = calls.find((call) => call.method === 'POST' && call.url.endsWith('/proposed-actions/10/reject'))
  assert(confirmCall?.body?.note === '客户已电话确认退票', `Expected confirm note payload, got ${JSON.stringify(confirmCall)}`)
  assert(rejectCall?.body?.reason === '客户撤销退票申请', `Expected reject reason payload, got ${JSON.stringify(rejectCall)}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant decision note controls browser uat')
} finally {
  await browser.close()
}
