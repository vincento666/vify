import { mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function envelope(data) {
  return { code: 200, message: 'success', data }
}

const story = {
  storyId: 'refund_baggage_parallel',
  title: '退票 + 行李额并行',
  sessionId: 51,
  sessionStatus: 'ACTIVE',
  customerName: '赵女士',
  maskedPhone: '138****0000',
  openingMessage: '我想退票，也想确认行李额。',
  taskCount: 2,
  pendingActionCount: 1,
  knowledgeBaseIds: [201],
}

const task = {
  id: 401,
  sessionId: 51,
  taskKey: 'refund_ticket:[REDACTED]',
  taskType: 'REFUND',
  businessKey: '[REDACTED]',
  shortId: 'refund-401',
  status: 'WAITING',
  workerType: 'chatflow_sop',
  workerRef: 'refund_ticket',
  checkpoint: { pendingPrompt: '请提供订单号' },
  lastResult: { missingFields: ['订单号'] },
  proposedActions: [],
  version: 1,
}

const metrics = {
  sessionId: 51,
  taskStatusCounts: { WAITING: 1 },
  proposedActionStatusCounts: { PENDING: 1 },
  humanConfirmation: { pending: 1, adopted: 0, terminal: 0, adoptionRate: 0 },
  eventCounts: { total: 1, byType: { run_started: 1 }, bySource: { demo_seed: 1 } },
  workerEventCounts: { total: 0, byType: {} },
  recentFailureReasons: [],
}

const operatorAudit = {
  sessionId: 51,
  list: [],
  total: 0,
}

const qaResult = {
  sessionId: 51,
  question: '退票和行李额可以并行处理吗？',
  answer: '可以并行处理，执行写操作前分别确认。',
  sources: [
    {
      knowledgeBaseId: 201,
      sourceType: 'FAQ',
      matchType: 'faq',
      score: 0.96,
      title: '退票和行李额并行处理',
      answerExcerpt: '退票和行李额任务可以并行推进。',
    },
  ],
  evidence: [
    {
      type: 'TASK_LEDGER',
      taskKey: 'refund_ticket:MU5137-8899',
      taskType: 'REFUND',
      status: 'WAITING',
      workerType: 'chatflow_sop',
      workerRef: 'refund_ticket',
      currentStep: 'collect_order_no',
    },
  ],
  contextSummary: {
    sessionId: 51,
    storyTitle: '退票 + 行李额并行',
    customer: { name: '赵女士', maskedPhone: '138****0000' },
    taskCount: 2,
    pendingActionCount: 1,
    eventCount: 1,
    knowledgeBaseIds: [201],
    latestEventTypes: ['run_started'],
    hostContext: { token: 'secret-token' },
  },
  warnings: ['No seeded FAQ or knowledge source matched the operator question.'],
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })

try {
  await page.route('**/api/v1/customer-assistant/**', async (route) => {
    const request = route.request()
    const url = request.url()
    const method = request.method()

    if (method === 'GET' && url.endsWith('/demo-stories')) {
      await route.fulfill({ json: envelope({ list: [story], total: 1 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/demo-stories/metrics')) {
      await route.fulfill({ json: envelope({ ...metrics, storyCount: 1, sessionCount: 1, stories: [] }) })
      return
    }
    if (method === 'GET' && url.endsWith('/worker-profiles')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/51/tasks')) {
      await route.fulfill({ json: envelope({ list: [task], total: 1 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/51/events')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
      return
    }
    if (method === 'GET' && url.endsWith('/sessions/51/proposed-actions')) {
      await route.fulfill({ json: envelope({ list: [], total: 0 }) })
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
    if (method === 'POST' && url.endsWith('/sessions/51/operator-knowledge-qa')) {
      const body = request.postDataJSON()
      assert(body.question === qaResult.question, `Expected Q&A question, got ${JSON.stringify(body)}`)
      await route.fulfill({ json: envelope(qaResult) })
      return
    }
    await route.fulfill({ status: 404, json: { code: 404, message: 'unexpected call', data: null } })
  })

  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })

  const qaPanel = page.getByTestId('operator-knowledge-qa-panel')
  await qaPanel.waitFor({ state: 'visible', timeout: 10000 })
  await qaPanel.getByRole('button', { name: '提问' }).click()
  await qaPanel.getByTestId('operator-knowledge-qa-answer').getByText('可以并行处理').waitFor({
    state: 'visible',
    timeout: 10000,
  })
  await qaPanel.getByTestId('operator-knowledge-qa-source').getByText('退票和行李额并行处理').waitFor({
    state: 'visible',
    timeout: 10000,
  })
  await qaPanel.getByTestId('operator-knowledge-qa-evidence').getByText('refund_ticket:[REDACTED]').waitFor({
    state: 'visible',
    timeout: 10000,
  })

  const qaText = await qaPanel.innerText()
  assert(qaText.includes('任务数：2'), `Expected context summary in Q&A panel, got ${qaText}`)
  assert(qaText.includes('知识库：201'), `Expected knowledge base summary in Q&A panel, got ${qaText}`)
  assert(qaText.includes('No seeded FAQ'), `Expected warning in Q&A panel, got ${qaText}`)
  assert(!qaText.includes('MU5137-8899'), 'Q&A panel leaked order-like task key')
  assert(!qaText.includes('secret-token'), 'Q&A panel leaked host context token')
  assert(!qaText.includes('hostContext'), 'Q&A panel leaked raw context field')

  if (screenshotPath) {
    mkdirSync(dirname(screenshotPath), { recursive: true })
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant operator knowledge qa e2e')
} finally {
  await browser.close()
}
