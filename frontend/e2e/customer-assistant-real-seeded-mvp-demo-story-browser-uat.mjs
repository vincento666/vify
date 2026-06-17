import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const __dirname = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(__dirname, '../..')
const artifactDir = process.env.HIFY_E2E_ARTIFACT_DIR
  || join(repoRoot, 'artifacts/slices/115-mvp-demo-story-browser-uat/115.1')
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || join(artifactDir, 'screenshots')
const reportPath = process.env.HIFY_E2E_REPORT || join(artifactDir, 'uat-report.json')
const notesPath = process.env.HIFY_E2E_NOTES || join(artifactDir, 'uat.md')
const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const demoHostContext = resolveDemoHostContext()

const expectedStories = {
  refund_baggage_parallel: {
    title: '退票 + 行李额并行',
    customerName: '赵女士',
    openingSnippet: '我要退',
    taskTexts: ['refund_ticket:MU5137-8899', 'baggage_service:MU5137-8899', 'RUNNING'],
    actionText: '并行处理退票与行李额确认',
    qaQuestion: '退票和行李额可以并行处理吗？',
    qaAnswer: '可以并行处理',
    qaSource: '退票和行李额',
    controlTaskKey: 'refund_ticket:MU5137-8899',
  },
  invoice_interrupt_flight_status: {
    title: '发票申请中途切航班动态',
    customerName: '陈先生',
    openingSnippet: '先帮我开行程单',
    taskTexts: ['invoice_apply:CA1301-20231027-8899', 'flight_status:CA1301', 'WAITING', 'PENDING'],
    actionText: '挂起发票申请并查询航班动态',
  },
  chatflow_block_resume_recommendation: {
    title: 'Chatflow 阻塞收集信息后生成坐席建议',
    customerName: '王先生',
    openingSnippet: '我要改签到明天上午',
    taskTexts: ['change_flight:missing-order', 'WAITING'],
    actionText: '补充订单号后恢复改签流程',
  },
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
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

async function api(page, path, options = {}) {
  const method = options.method || 'GET'
  const url = `${baseUrl}/api/v1${path}`
  const response = method === 'GET'
    ? await page.request.get(url)
    : await page.request.fetch(url, {
      method,
      data: options.data,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    })
  assert(response.ok(), `${path} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${path} API ${payload.message}`)
  return payload.data
}

async function waitForTestIdText(page, testId, text, timeout = 10000) {
  await page.waitForFunction(
    ({ testId: targetTestId, text: expectedText }) => {
      const element = document.querySelector(`[data-testid="${targetTestId}"]`)
      return Boolean(element?.textContent?.includes(expectedText))
    },
    { testId, text },
    { timeout },
  )
}

async function waitForStory(page, story, expected) {
  await page.getByText(`Session #${story.sessionId}`).first().waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText(expected.customerName).first().waitFor({ state: 'visible', timeout: 10000 })
  await waitForTestIdText(page, 'customer-conversation-lane', expected.openingSnippet)
}

async function selectStory(page, story, expected) {
  const storyStrip = page.getByTestId('customer-assistant-demo-stories')
  await storyStrip.getByRole('button', { name: new RegExp(escapeRegExp(expected.title)) }).click()
  await waitForStory(page, story, expected)
}

async function verifyWorkbenchStory(page, story, expected) {
  await waitForStory(page, story, expected)

  const customerLane = await page.getByTestId('customer-conversation-lane').innerText()
  assert(customerLane.includes(expected.openingSnippet), `${story.storyId}: missing customer opening`)

  const taskLedger = page.getByTestId('operator-task-ledger')
  const taskLedgerText = await taskLedger.innerText()
  for (const text of expected.taskTexts) {
    assert(taskLedgerText.includes(text), `${story.storyId}: task ledger missing ${text}`)
  }

  const actionPanel = page.getByTestId('operator-proposed-actions-panel')
  await actionPanel.getByText(expected.actionText, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })

  const metricsText = await page.getByTestId('operator-metrics-panel').innerText()
  assert(metricsText.includes('待确认动作'), `${story.storyId}: metrics panel missing pending action tile`)
  assert(metricsText.includes('活跃任务'), `${story.storyId}: metrics panel missing active task tile`)

  const evalText = await page.getByTestId('operator-eval-observability-panel').innerText()
  assert(evalText.includes('评估观测'), `${story.storyId}: eval panel missing heading`)
  assert(evalText.includes('Worker 执行'), `${story.storyId}: eval panel missing worker execution section`)
  assert(
    expected.taskTexts.some((text) => evalText.includes(text)),
    `${story.storyId}: eval panel missing seeded task evidence`,
  )

  const pageMetrics = await page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    bodyLength: document.body.innerText.trim().length,
  }))
  assert(pageMetrics.overflowX <= 0, `${story.storyId}: horizontal overflow ${pageMetrics.overflowX}`)
  assert(pageMetrics.bodyLength > 0, `${story.storyId}: expected visible body text`)

  return {
    storyId: story.storyId,
    title: story.title,
    sessionId: story.sessionId,
    taskTexts: expected.taskTexts,
    actionText: expected.actionText,
    pageMetrics,
  }
}

async function verifyWorkerProfilePanel(page) {
  const profiles = await api(page, '/customer-assistant/worker-profiles')
  assert(profiles.total >= 1, `Expected at least one worker profile, got ${profiles.total}`)
  const panel = page.getByTestId('operator-worker-profile-config-panel')
  await panel.getByText('Worker 配置').waitFor({ state: 'visible', timeout: 10000 })
  const panelText = await panel.innerText()
  assert(panelText.includes('refund_ticket_chatflow'), 'Worker profile panel missing refund profile')
  assert(panelText.includes('customer_assistant_chatflow_default'), 'Worker profile panel missing model policy')
  assert(panelText.includes('manual_confirm'), 'Worker profile panel missing risk policy')
  return {
    total: profiles.total,
    profileIds: profiles.list.map((profile) => profile.profileId),
  }
}

async function askOperatorKnowledgeQuestion(page, story, expected) {
  const qaPanel = page.getByTestId('operator-knowledge-qa-panel')
  await qaPanel.waitFor({ state: 'visible', timeout: 10000 })
  await qaPanel.getByTestId('operator-knowledge-qa-question').fill(expected.qaQuestion)
  await qaPanel.getByRole('button', { name: '提问' }).click()
  await qaPanel.getByTestId('operator-knowledge-qa-answer').getByText(expected.qaAnswer).waitFor({
    state: 'visible',
    timeout: 10000,
  })
  await qaPanel.getByTestId('operator-knowledge-qa-source').getByText(expected.qaSource).waitFor({
    state: 'visible',
    timeout: 10000,
  })
  const qaText = await qaPanel.innerText()
  assert(qaText.includes('任务数：2'), 'Q&A panel missing context summary task count')
  assert(!qaText.includes('MU5137-8899'), 'Q&A panel leaked raw order id')
  assert(!qaText.includes('hostContext'), 'Q&A panel leaked raw host context')
  return {
    storyId: story.storyId,
    question: expected.qaQuestion,
    answerVisible: expected.qaAnswer,
    sourceVisible: expected.qaSource,
    redactionChecked: true,
  }
}

async function confirmCancelControl(page, story, expected) {
  const taskLedger = page.getByTestId('operator-task-ledger')
  const taskRow = taskLedger.locator('.task-row').filter({ hasText: expected.controlTaskKey }).first()
  await taskRow.getByText('RUNNING').waitFor({ state: 'visible', timeout: 10000 })
  await taskRow.getByRole('button', { name: '取消' }).click()

  const actionTitle = `取消任务：${expected.controlTaskKey}`
  const actionPanel = page.getByTestId('operator-proposed-actions-panel')
  const actionRow = actionPanel.locator('.action-row').filter({ hasText: actionTitle }).first()
  await actionRow.getByText('PENDING').waitFor({ state: 'visible', timeout: 10000 })
  await actionRow.locator('button').filter({ hasText: '确认任务变更' }).click()
  await actionRow.getByText('CONFIRMED').waitFor({ state: 'visible', timeout: 10000 })
  await taskRow.getByText('CANCELLED').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('operator-event-timeline').getByText('proposed_task_command_confirmed').waitFor({
    state: 'visible',
    timeout: 10000,
  })

  const metrics = await api(page, `/customer-assistant/sessions/${story.sessionId}/metrics`)
  assert(metrics.humanConfirmation.adopted >= 1, 'Expected confirmed task command to count as adopted')
  assert(metrics.proposedActionStatusCounts.CONFIRMED >= 1, 'Expected confirmed action count after operator control')

  return {
    storyId: story.storyId,
    taskKey: expected.controlTaskKey,
    actionTitle,
    confirmed: true,
    adopted: metrics.humanConfirmation.adopted,
    pending: metrics.humanConfirmation.pending,
  }
}

async function saveScreenshot(page, report, name) {
  mkdirSync(screenshotDir, { recursive: true })
  const path = join(screenshotDir, `${name}.png`)
  await page.screenshot({ path, fullPage: true })
  report.screenshots.push(path)
}

function writeReport(report) {
  mkdirSync(dirname(reportPath), { recursive: true })
  writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`)
  const storyLines = report.stories.map((story) => `- ${story.storyId}: session ${story.sessionId}`).join('\n')
  const screenshotLines = report.screenshots.map((path) => `- ${path}`).join('\n')
  writeFileSync(
    notesPath,
    [
      '# UAT Notes',
      '',
      `Base URL: ${report.baseUrl}`,
      `Host tenant: ${report.hostContext.tenantId}`,
      '',
      '## Verified Stories',
      '',
      storyLines,
      '',
      '## Panels',
      '',
      `- Worker profiles: ${report.workerProfiles.profileIds.join(', ')}`,
      `- Operator Q&A: ${report.operatorKnowledgeQa.answerVisible}`,
      `- Confirm path: ${report.confirmPath.actionTitle}`,
      '',
      '## Screenshots',
      '',
      screenshotLines,
      '',
    ].join('\n'),
  )
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const pageErrors = []
page.on('pageerror', (error) => {
  pageErrors.push(error.message)
})

const report = {
  specId: '115-mvp-demo-story-browser-uat',
  baseUrl,
  hostContext: demoHostContext,
  stories: [],
  workerProfiles: null,
  operatorKnowledgeQa: null,
  confirmPath: null,
  screenshots: [],
}

try {
  await page.addInitScript((hostContext) => {
    globalThis.__HIFY_HOST__ = {
      ...hostContext,
      apiBaseUrl: '/api',
    }
  }, demoHostContext)

  const stories = await api(page, '/customer-assistant/demo-stories')
  const storyIds = stories.list.map((story) => story.storyId)
  for (const storyId of Object.keys(expectedStories)) {
    assert(storyIds.includes(storyId), `Missing seeded story ${storyId}`)
  }
  const metrics = await api(page, '/customer-assistant/demo-stories/metrics')
  assert(metrics.storyCount >= 3, `Expected at least 3 demo stories in metrics, got ${metrics.storyCount}`)
  assert(metrics.humanConfirmation.pending >= 3, 'Expected seeded demo metrics to include pending confirmations')

  const byId = Object.fromEntries(stories.list.map((story) => [story.storyId, story]))
  const invoice = byId.invoice_interrupt_flight_status
  const refund = byId.refund_baggage_parallel
  const chatflow = byId.chatflow_block_resume_recommendation

  await page.goto(`${baseUrl}/customer-assistant?view=demo&story=${encodeURIComponent(invoice.storyId)}`, {
    waitUntil: 'networkidle',
  })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('customer-assistant-demo-metrics').getByText('演示总览').waitFor({
    state: 'visible',
    timeout: 10000,
  })
  await waitForStory(page, invoice, expectedStories.invoice_interrupt_flight_status)
  let url = new URL(page.url())
  assert(url.searchParams.get('story') === invoice.storyId, `Expected invoice deeplink story query, got ${url}`)
  assert(url.searchParams.get('view') === 'demo', `Expected view query to be preserved, got ${url}`)
  report.stories.push(await verifyWorkbenchStory(page, invoice, expectedStories.invoice_interrupt_flight_status))
  await saveScreenshot(page, report, 'invoice-deeplink-story')

  await selectStory(page, refund, expectedStories.refund_baggage_parallel)
  url = new URL(page.url())
  assert(url.searchParams.get('story') === refund.storyId, `Expected refund story query after switch, got ${url}`)
  assert(url.searchParams.get('view') === 'demo', `Expected view query after story switch, got ${url}`)
  report.stories.push(await verifyWorkbenchStory(page, refund, expectedStories.refund_baggage_parallel))
  report.workerProfiles = await verifyWorkerProfilePanel(page)
  report.operatorKnowledgeQa = await askOperatorKnowledgeQuestion(page, refund, expectedStories.refund_baggage_parallel)
  report.confirmPath = await confirmCancelControl(page, refund, expectedStories.refund_baggage_parallel)
  await saveScreenshot(page, report, 'refund-qa-confirmed')

  await selectStory(page, chatflow, expectedStories.chatflow_block_resume_recommendation)
  report.stories.push(await verifyWorkbenchStory(page, chatflow, expectedStories.chatflow_block_resume_recommendation))
  await page
    .getByTestId('operator-task-ledger')
    .locator('.task-row')
    .filter({ hasText: 'change_flight:missing-order' })
    .first()
    .getByRole('button', { name: '恢复' })
    .waitFor({ state: 'visible', timeout: 10000 })
  await saveScreenshot(page, report, 'chatflow-resume-story')

  assert(pageErrors.length === 0, `Unexpected browser page errors: ${pageErrors.join('; ')}`)
  writeReport(report)
  console.log('PASS customer assistant real seeded mvp demo story browser uat')
} finally {
  await browser.close()
}
