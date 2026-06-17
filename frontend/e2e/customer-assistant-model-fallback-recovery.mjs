import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function envelope(data) {
  return { code: 200, message: 'success', data }
}

const failedTask = {
  id: 420,
  sessionId: 52,
  taskKey: 'refund_ticket:fallback',
  taskType: 'REFUND',
  businessKey: 'order-redacted',
  shortId: 'refund-420',
  status: 'FAILED',
  workerType: 'react_worker',
  workerRef: 'refund_retry_agent',
  checkpoint: { currentStep: 'model_fallback' },
  lastResult: {
    status: 'FAILED',
    error: '模型结构化输出不合规，已改用确定性回退。',
  },
  proposedActions: [],
  version: 2,
}

const fallbackEvents = [
  {
    id: 1200,
    sessionId: 52,
    runId: 88,
    sequence: 1,
    type: 'task_recognized',
    visibility: 'operator',
    source: 'customer_assistant',
    taskId: 420,
    payload: {
      recognized: [
        {
          taskKey: 'refund_ticket:fallback',
          taskType: 'REFUND',
          workerType: 'react_worker',
          workerRef: 'refund_retry_agent',
        },
      ],
    },
  },
  {
    id: 1201,
    sessionId: 52,
    runId: 88,
    sequence: 2,
    type: 'llm_primary_fallback',
    visibility: 'operator',
    source: 'llm_primary',
    taskId: 420,
    payload: {
      phase: 'task_recognition',
      reason: 'schema_failure phone 13800138000',
    },
  },
  {
    id: 1202,
    sessionId: 52,
    runId: 88,
    sequence: 3,
    type: 'worker_failed',
    visibility: 'operator',
    source: 'react_worker',
    taskId: 420,
    payload: {
      reason: 'schema_failure phone 13800138000',
    },
  },
]

const turnResult = {
  runId: 88,
  sessionId: 52,
  replyType: 'DRAFT',
  operatorRecommendation: '模型结构化输出异常，当前已使用确定性任务识别回退；失败任务可由坐席重试。',
  customerReplyDraft: '我已经记录您的退票诉求，正在为您重新核验。',
  taskSummaries: [failedTask],
  proposedActions: [],
  warnings: ['模型回退后关联任务失败，请坐席检查策略并决定是否重试。'],
  events: fallbackEvents,
  replayed: false,
}

const fallbackMetrics = {
  sessionId: 52,
  taskStatusCounts: { FAILED: 1 },
  proposedActionStatusCounts: {},
  humanConfirmation: { pending: 0, adopted: 0, terminal: 0, adoptionRate: 0 },
  eventCounts: {
    total: 3,
    byType: { task_recognized: 1, llm_primary_fallback: 1, worker_failed: 1 },
    bySource: { customer_assistant: 1, llm_primary: 1, react_worker: 1 },
  },
  workerEventCounts: { total: 1, byType: { worker_failed: 1 } },
  recentFailureReasons: [
    {
      taskId: 420,
      taskType: 'REFUND',
      source: 'react_worker',
      reason: 'schema_failure phone 13800138000',
    },
  ],
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
      await route.fulfill({ json: envelope(fallbackMetrics) })
      return
    }
    if (method === 'GET' && url.endsWith('/worker-profiles')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions')) {
      await route.fulfill({ json: envelope({ id: 52, status: 'ACTIVE', context: {} }) })
      return
    }
    if (method === 'POST' && url.endsWith('/sessions/52/turns')) {
      await route.fulfill({ json: envelope(turnResult) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/52/tasks')) {
      await route.fulfill({ json: envelope({ list: [failedTask], total: 1 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/52/events')) {
      await route.fulfill({ json: envelope({ list: fallbackEvents, total: fallbackEvents.length }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/52/proposed-actions')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/52/metrics')) {
      await route.fulfill({ json: envelope(fallbackMetrics) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/52/operator-audit')) {
      await route.fulfill({ json: envelope({ sessionId: 52, list: [], total: 0 }) })
      return
    }
    await route.fulfill({ status: 404, json: { code: 404, message: 'unexpected call', data: null } })
  })

  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('button', { name: '模拟客户输入' }).click()

  const evalPanel = page.getByTestId('operator-eval-observability-panel')
  await evalPanel.getByText('模型/回退证据').waitFor({ state: 'visible', timeout: 10000 })
  await evalPanel.getByText('模型回退').waitFor({ state: 'visible', timeout: 10000 })
  await evalPanel.getByText('task_recognition · schema_failure phone [REDACTED]').first().waitFor({
    state: 'visible',
    timeout: 10000,
  })
  await evalPanel.getByText('恢复建议').waitFor({ state: 'visible', timeout: 10000 })
  await evalPanel.getByText('模型异常恢复').waitFor({ state: 'visible', timeout: 10000 })
  await evalPanel.getByText('若关联任务失败，可在任务台账点击重试。').waitFor({
    state: 'visible',
    timeout: 10000,
  })

  const taskLedger = page.getByTestId('operator-task-ledger')
  const failedTaskRow = taskLedger.locator('.task-row').filter({ hasText: 'refund_ticket:fallback' })
  await failedTaskRow.getByText('FAILED').waitFor({ state: 'visible', timeout: 10000 })
  await failedTaskRow.getByRole('button', { name: '重试' }).waitFor({ state: 'visible', timeout: 10000 })

  const pageText = await page.locator('body').innerText()
  const leakedPhoneLines = pageText.split('\n').filter((line) => line.includes('13800138000'))
  assert(
    leakedPhoneLines.length === 0,
    `UAT page must not expose raw customer phone. Leaks: ${leakedPhoneLines.join(' | ')}`,
  )
  assert(pageText.includes('[REDACTED]'), 'UAT page should show redacted evidence instead of raw sensitive values')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant model fallback recovery e2e')
} finally {
  await browser.close()
}
