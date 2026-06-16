import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function envelope(data) {
  return { code: 200, message: 'success', data }
}

const task = {
  id: 401,
  sessionId: 51,
  taskKey: 'refund_ticket:MU5137-8899',
  taskType: 'REFUND',
  businessKey: 'MU5137-8899',
  shortId: 'refund-401',
  status: 'WAITING',
  workerType: 'chatflow_sop',
  workerRef: 'refund_ticket',
  checkpoint: { pendingPrompt: '请提供订单号' },
  lastResult: { missingFields: ['订单号'] },
  proposedActions: [],
  version: 1,
}

const action = {
  id: 91,
  sessionId: 51,
  runId: 61,
  taskId: 401,
  actionKey: 'refund:submit',
  actionType: 'submit_refund',
  title: '提交退票申请',
  payload: { orderNo: '[REDACTED]' },
  status: 'CONFIRMED',
}

const turnResult = {
  runId: 61,
  sessionId: 51,
  replyType: 'DRAFT',
  operatorRecommendation: '请核对退票规则并查看操作审计。',
  customerReplyDraft: '我会继续为您核验退票信息。',
  taskSummaries: [task],
  proposedActions: [action],
  warnings: [],
  events: [
    {
      id: 951,
      sessionId: 51,
      runId: 61,
      sequence: 1,
      type: 'task_control_proposed',
      visibility: 'operator',
      source: 'operator_advisory',
      actor: 'operator',
      taskId: 401,
      payload: { actionId: 91, controlType: 'retry', taskKey: 'refund_ticket:[REDACTED]' },
    },
  ],
  replayed: false,
}

const metrics = {
  sessionId: 51,
  taskStatusCounts: { WAITING: 1 },
  proposedActionStatusCounts: { CONFIRMED: 1 },
  humanConfirmation: { pending: 0, adopted: 1, terminal: 1, adoptionRate: 1 },
  eventCounts: { total: 2, byType: { task_control_proposed: 1 }, bySource: { operator_advisory: 1 } },
  workerEventCounts: { total: 0, byType: {} },
  recentFailureReasons: [],
}

const operatorAudit = {
  sessionId: 51,
  list: [
    {
      id: 701,
      sequence: 1,
      eventType: 'task_control_proposed',
      title: '任务控制已提出',
      actor: 'operator',
      source: 'operator_advisory',
      status: 'PENDING_CONFIRMATION',
      targetType: 'action',
      targetId: 91,
      summary: 'retry requested for refund_ticket:[REDACTED]',
      createdAt: '2026-06-17T06:10:00',
    },
    {
      id: 702,
      sequence: 2,
      eventType: 'proposed_action_confirmed',
      title: '拟议动作已确认',
      actor: 'operator',
      source: 'operator_advisory',
      status: 'CONFIRMED',
      targetType: 'action',
      targetId: 91,
      summary: 'submit_refund CONFIRMED',
      createdAt: '2026-06-17T06:11:00',
    },
  ],
  total: 2,
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })

try {
  await page.route('**/api/v1/customer-assistant/**', async (route) => {
    const request = route.request()
    const url = request.url()
    const method = request.method()

    if (method === 'GET' && url.endsWith('/demo-stories')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/demo-stories/metrics')) {
      await route.fulfill({ json: envelope({ ...metrics, storyCount: 0, sessionCount: 0, stories: [] }) })
      return
    }
    if (method === 'GET' && url.endsWith('/worker-profiles')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions')) {
      await route.fulfill({ json: envelope({ id: 51, status: 'ACTIVE', context: {} }) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions/51/turns')) {
      await route.fulfill({ json: envelope(turnResult) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/51/tasks')) {
      await route.fulfill({ json: envelope({ list: [task], total: 1 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/51/events')) {
      await route.fulfill({ json: envelope({ list: turnResult.events, total: turnResult.events.length }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/51/proposed-actions')) {
      await route.fulfill({ json: envelope({ list: [action], total: 1 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/51/metrics')) {
      await route.fulfill({ json: envelope(metrics) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/51/operator-audit')) {
      await route.fulfill({ json: envelope(operatorAudit) })
      return
    }
    await route.fulfill({ status: 404, json: { code: 404, message: 'unexpected call', data: null } })
  })

  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('button', { name: '模拟客户输入' }).click()

  const auditPanel = page.getByTestId('operator-audit-panel')
  await auditPanel.getByText('任务控制已提出').waitFor({ state: 'visible', timeout: 10000 })
  await auditPanel.getByText('拟议动作已确认').waitFor({ state: 'visible', timeout: 10000 })
  const auditText = await auditPanel.innerText()

  assert(auditText.includes('submit_refund CONFIRMED'), `Expected confirmed audit row, got ${auditText}`)
  assert(!auditText.includes('13812345678'), 'Audit panel leaked phone number')
  assert(!auditText.includes('MU5137-8899'), 'Audit panel leaked order number')
  assert(!auditText.includes('secret-token'), 'Audit panel leaked token')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant operator audit e2e')
} finally {
  await browser.close()
}
