import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || ''
const reportPath = process.env.HIFY_E2E_REPORT || ''
const demoHostContext = resolveDemoHostContext()

const expectedStories = [
  {
    storyId: 'refund_baggage_parallel',
    title: '退票 + 行李额并行',
    customerName: '赵女士',
    opening: '我要退 [REDACTED] 的票',
    ledgerTexts: ['refund_ticket:MU5137-8899', 'baggage_service:MU5137-8899', 'RUNNING'],
    actionText: '并行处理退票与行李额确认',
  },
  {
    storyId: 'invoice_interrupt_flight_status',
    title: '发票申请中途切航班动态',
    customerName: '陈先生',
    opening: '先帮我开行程单',
    ledgerTexts: ['invoice_apply:CA1301-20231027-8899', 'flight_status:CA1301', 'WAITING', 'PENDING'],
    actionText: '挂起发票申请并查询航班动态',
  },
  {
    storyId: 'chatflow_block_resume_recommendation',
    title: 'Chatflow 阻塞收集信息后生成坐席建议',
    customerName: '王先生',
    opening: '我要改签到明天上午',
    ledgerTexts: ['change_flight:missing-order', 'WAITING'],
    actionText: '补充订单号后恢复改签流程',
    recoveryButton: '恢复',
    recoveryActionText: '恢复任务：change_flight:missing-order',
  },
]

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function api(page, path) {
  const response = await page.request.get(`${baseUrl}/api/v1${path}`)
  assert(response.ok(), `${path} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${path} API ${payload.message}`)
  return payload.data
}

async function selectStory(page, story) {
  const storyStrip = page.getByTestId('customer-assistant-demo-stories')
  await storyStrip.getByText(story.title).waitFor({ state: 'visible', timeout: 10000 })
  await storyStrip.getByRole('button', { name: new RegExp(escapeRegExp(story.title)) }).click()
  await page.getByText(/Session #/).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText(story.customerName).first().waitFor({ state: 'visible', timeout: 10000 })
}

async function verifyStory(page, story) {
  await selectStory(page, story)
  await waitForTestIdText(page, 'customer-conversation-lane', story.opening)
  const customerLane = await page.getByTestId('customer-conversation-lane').innerText()
  assert(customerLane.includes(story.opening), `${story.storyId}: missing opening message`)

  const taskLedger = page.getByTestId('operator-task-ledger')
  const ledgerText = await taskLedger.innerText()
  for (const text of story.ledgerTexts) {
    assert(ledgerText.includes(text), `${story.storyId}: task ledger missing ${text}`)
  }

  const actionPanel = page.getByTestId('operator-proposed-actions-panel')
  await actionPanel.getByText(story.actionText, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  const metricsText = await page.getByTestId('operator-metrics-panel').innerText()
  assert(metricsText.includes('活跃任务'), `${story.storyId}: metrics panel should show active task tile`)
  assert(metricsText.includes('待确认动作'), `${story.storyId}: metrics panel should show pending action tile`)

  if (story.recoveryButton) {
    const taskRow = taskLedger.locator('.task-row').filter({ hasText: story.ledgerTexts[0] }).first()
    await taskRow.getByRole('button', { name: story.recoveryButton }).click()
    await actionPanel.getByText(story.recoveryActionText).waitFor({ state: 'visible', timeout: 10000 })
  }

  const pageMetrics = await page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    bodyLength: document.body.innerText.trim().length,
  }))
  assert(pageMetrics.overflowX <= 0, `${story.storyId}: horizontal overflow ${pageMetrics.overflowX}`)
  assert(pageMetrics.bodyLength > 0, `${story.storyId}: expected visible body text`)

  if (screenshotDir) {
    mkdirSync(screenshotDir, { recursive: true })
    await page.screenshot({ path: `${screenshotDir}/${story.storyId}.png`, fullPage: true })
  }

  return { storyId: story.storyId, title: story.title, verified: true, pageMetrics }
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

async function waitForTestIdText(page, testId, text) {
  await page.waitForFunction(
    ({ testId: targetTestId, text: expectedText }) => {
      const element = document.querySelector(`[data-testid="${targetTestId}"]`)
      return Boolean(element?.textContent?.includes(expectedText))
    },
    { testId, text },
    { timeout: 10000 },
  )
}

function resolveDemoHostContext() {
  if (process.env.HIFY_MVP_DEMO_HOST_CONTEXT_JSON) {
    return JSON.parse(process.env.HIFY_MVP_DEMO_HOST_CONTEXT_JSON)
  }
  return {
    actorId: 'mvp-demo-operator',
    actorName: 'MVP Demo Operator',
    tenantId: 'mvp-demo-tenant',
    orgId: 'mvp-demo-org',
    roles: ['customer_service_operator'],
    permissions: ['customer_assistant:read', 'customer_assistant:operate'],
    source: 'mvp-demo-shell',
    locale: 'zh-CN',
  }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const report = { baseUrl, hostContext: demoHostContext, stories: [] }

try {
  await page.addInitScript((hostContext) => {
    globalThis.__HIFY_HOST__ = {
      ...hostContext,
      apiBaseUrl: '/api',
    }
  }, demoHostContext)
  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })

  const stories = await api(page, '/customer-assistant/demo-stories')
  const storyIds = stories.list.map((story) => story.storyId)
  assert(stories.total === 3, `Expected 3 seeded stories, got ${stories.total}`)
  assert(
    expectedStories.every((story) => storyIds.includes(story.storyId)),
    `Missing seeded stories: ${expectedStories.map((story) => story.storyId).filter((storyId) => !storyIds.includes(storyId)).join(', ')}`,
  )

  for (const story of expectedStories) {
    report.stories.push(await verifyStory(page, story))
  }

  if (reportPath) {
    mkdirSync(dirname(reportPath), { recursive: true })
    writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`)
  }

  console.log('PASS mvp demo seeded storylines e2e')
} finally {
  await browser.close()
}
