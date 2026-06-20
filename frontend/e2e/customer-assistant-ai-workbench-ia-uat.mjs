import { mkdir, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const __dirname = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(__dirname, '../..')
const sliceRoot = join(
  repoRoot,
  'artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence',
)
const artifactDir = join(sliceRoot, 'slice-c-uat')
const screenshotDir = join(sliceRoot, 'screenshots')
const notesPath = join(artifactDir, 'uat.md')
const targetUrl = normalizeTargetUrl(
  process.env.BASE_URL
    || process.env.HIFY_E2E_BASE_URL
    || 'http://127.0.0.1:5173/customer-assistant',
)

const storyId = 'slice-c-ai-workbench-ia'
const sessionId = 207
const taskId = 20701
const actionId = 20709

const story = {
  storyId,
  title: 'Slice C IA 收敛',
  sessionId,
  sessionStatus: 'ACTIVE',
  customerName: '林女士',
  maskedPhone: '139****0207',
  openingMessage: '我要退 MU5137 的票，也想确认行李额。',
  taskCount: 1,
  pendingActionCount: 1,
  knowledgeBaseIds: [201],
}

const task = {
  id: taskId,
  sessionId,
  taskKey: 'refund_ticket:MU5137-8899',
  taskType: 'REFUND',
  businessKey: 'refund_ticket',
  shortId: 'refund-207',
  status: 'WAITING',
  workerType: 'chatflow_sop',
  workerRef: 'refund_ticket',
  checkpoint: {
    currentStep: 'collect_order_no',
    pendingPrompt: '请补充退票订单号后继续办理。',
    collected: { flightNo: 'MU5137' },
  },
  lastResult: {
    status: 'WAITING',
    missingFields: ['订单号'],
    operatorRecommendation: '先安抚旅客，确认退票订单号，再提示行李额规则可并行查询。',
  },
  proposedActions: [],
  version: 1,
}

const proposedAction = {
  id: actionId,
  sessionId,
  runId: 20731,
  taskId,
  actionKey: 'refund_ticket:submit:MU5137-8899',
  actionType: 'SUBMIT_REFUND',
  title: '高敏确认：提交 MU5137 退票申请',
  payload: {
    orderNo: 'MU5137-8899',
    amount: 860,
    riskLevel: 'HIGH',
  },
  status: 'PENDING',
}

const events = [
  {
    id: 207001,
    sessionId,
    runId: 20731,
    sequence: 1,
    type: 'run_started',
    visibility: 'normal',
    source: 'slice_c_uat',
    actor: 'customer',
    taskId: null,
    parentSpanId: null,
    spanId: 'run-20731',
    payload: { storyId },
    createdAt: '2026-06-20T00:00:00Z',
  },
  {
    id: 207002,
    sessionId,
    runId: 20731,
    sequence: 2,
    type: 'task_recognized',
    visibility: 'normal',
    source: 'customer_assistant',
    actor: 'system',
    taskId,
    parentSpanId: 'run-20731',
    spanId: 'task-20701',
    payload: {
      taskKey: task.taskKey,
      taskType: task.taskType,
      workerType: task.workerType,
      workerRef: task.workerRef,
      profileRefs: {
        profileId: 'refund_ticket_chatflow',
        modelPolicyRef: 'customer_assistant_chatflow_default',
        promptRef: 'refund_ticket_sop_prompt',
        riskPolicyRef: 'manual_confirm',
      },
    },
    observability: {
      profileRefs: {
        profileId: 'refund_ticket_chatflow',
        modelPolicyRef: 'customer_assistant_chatflow_default',
        promptRef: 'refund_ticket_sop_prompt',
        riskPolicyRef: 'manual_confirm',
      },
    },
    createdAt: '2026-06-20T00:00:01Z',
  },
  {
    id: 207003,
    sessionId,
    runId: 20731,
    sequence: 3,
    type: 'recommendation_generated',
    visibility: 'normal',
    source: 'operator_advisory',
    actor: 'assistant',
    taskId,
    parentSpanId: 'run-20731',
    spanId: 'recommendation-207',
    payload: {
      operatorRecommendation: '建议回复：我先帮您核对退票信息，行李额规则也会同步确认。',
    },
    createdAt: '2026-06-20T00:00:02Z',
  },
]

const workerProfiles = {
  list: [
    {
      profileId: 'refund_ticket_chatflow',
      taskKey: 'refund_ticket',
      taskType: 'REFUND',
      workerType: 'chatflow_sop',
      workerRef: 'refund_ticket',
      modelPolicyRef: 'customer_assistant_chatflow_default',
      promptRef: 'refund_ticket_sop_prompt',
      toolRefs: ['refund_policy_lookup'],
      toolPolicyRef: 'customer_assistant_worker_tool_default',
      riskPolicyRef: 'manual_confirm',
      outputSchemaRef: 'customer_assistant_worker_result_v1',
      enabled: true,
    },
  ],
  total: 1,
}

function normalizeTargetUrl(value) {
  const url = new URL(value)
  if (url.pathname === '/' || url.pathname === '') {
    url.pathname = '/customer-assistant'
  }
  return url.toString()
}

function withQuery(url, entries) {
  const nextUrl = new URL(url)
  for (const [key, value] of Object.entries(entries)) {
    nextUrl.searchParams.set(key, value)
  }
  return nextUrl.toString()
}

function envelope(data) {
  return { code: 200, message: 'success', data }
}

function screenshotName(name) {
  return join(screenshotDir, `${name}.png`)
}

async function saveScreenshot(page, screenshots, name) {
  await mkdir(screenshotDir, { recursive: true })
  const path = screenshotName(name)
  await page.screenshot({ path, fullPage: true })
  screenshots.push(path)
}

async function isVisible(locator, timeout = 500) {
  try {
    await locator.waitFor({ state: 'visible', timeout })
    return true
  } catch {
    return false
  }
}

async function visibleText(locator) {
  if (!(await isVisible(locator, 100))) return ''
  return locator.innerText()
}

async function tabLabels(page) {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll('[data-testid="operator-ai-workbench-tabs"] button'))
      .map((button) => button.textContent?.trim() || '')
      .filter(Boolean),
  )
}

async function clickWorkbenchTab(page, label, failures) {
  const button = page.getByTestId('operator-ai-workbench-tabs').getByRole('tab', { name: label, exact: true })
  if (!(await isVisible(button, 1500))) {
    failures.push(`Missing workbench tab: ${label}`)
    return false
  }
  await button.click()
  return true
}

async function expectVisibleTextInFirstScreen(page, pane, text, failures) {
  const locator = pane.getByText(text, { exact: false }).first()
  if (!(await isVisible(locator, 1500))) {
    failures.push(`Focus first screen missing visible section: ${text}`)
    return
  }

  const box = await locator.boundingBox()
  const viewport = page.viewportSize()
  if (!box || !viewport) {
    failures.push(`Could not measure first-screen section: ${text}`)
    return
  }
  if (box.y < 0 || box.y + box.height > viewport.height) {
    failures.push(`Focus section is not in the first viewport: ${text}`)
  }
}

async function expectNoVisibleDescendant(root, testId, failures, label = testId) {
  const count = await root.getByTestId(testId).count()
  for (let index = 0; index < count; index += 1) {
    if (await root.getByTestId(testId).nth(index).isVisible()) {
      failures.push(`Unexpected visible ${label} inside assistant chat`)
      return
    }
  }
}

async function setupApiMocks(page) {
  await page.route('**/api/v1/customer-assistant/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    const method = request.method()

    if (method === 'GET' && path.endsWith('/demo-stories')) {
      await route.fulfill({ json: envelope({ list: [story], total: 1 }) })
      return
    }
    if (method === 'GET' && path.endsWith('/demo-stories/metrics')) {
      await route.fulfill({
        json: envelope({
          storyCount: 1,
          sessionCount: 1,
          taskStatusCounts: { WAITING: 1 },
          proposedActionStatusCounts: { PENDING: 1 },
          humanConfirmation: { pending: 1, adopted: 0, terminal: 0, adoptionRate: 0 },
          eventCounts: { total: events.length, byType: { run_started: 1, task_recognized: 1 }, bySource: {} },
          workerEventCounts: { total: 0, byType: {} },
          recentFailureReasons: [],
          stories: [],
        }),
      })
      return
    }
    if (method === 'GET' && path.endsWith('/worker-profiles')) {
      await route.fulfill({ json: envelope(workerProfiles) })
      return
    }
    if (method === 'GET' && path.endsWith(`/sessions/${sessionId}/tasks`)) {
      await route.fulfill({ json: envelope({ list: [task], total: 1 }) })
      return
    }
    if (method === 'GET' && path.endsWith(`/sessions/${sessionId}/proposed-actions`)) {
      await route.fulfill({ json: envelope({ list: [proposedAction], total: 1 }) })
      return
    }
    if (method === 'GET' && path.endsWith(`/sessions/${sessionId}/events`)) {
      await route.fulfill({ json: envelope({ list: events, total: events.length }) })
      return
    }
    if (method === 'GET' && path.endsWith(`/sessions/${sessionId}/metrics`)) {
      await route.fulfill({
        json: envelope({
          sessionId,
          taskStatusCounts: { WAITING: 1 },
          proposedActionStatusCounts: { PENDING: 1 },
          humanConfirmation: { pending: 1, adopted: 0, terminal: 0, adoptionRate: 0 },
          eventCounts: { total: events.length, byType: { run_started: 1, task_recognized: 1 }, bySource: {} },
          workerEventCounts: { total: 0, byType: {} },
          recentFailureReasons: [],
        }),
      })
      return
    }
    if (method === 'GET' && path.endsWith(`/sessions/${sessionId}/operator-audit`)) {
      await route.fulfill({
        json: envelope({
          sessionId,
          list: [
            {
              id: 207701,
              sequence: 7,
              eventType: 'proposed_action_created',
              title: '高敏确认待处理',
              actor: 'assistant',
              source: 'operator_advisory',
              status: 'PENDING',
              targetType: 'action',
              targetId: actionId,
              summary: '提交退票申请需要人工确认',
              createdAt: '2026-06-20T00:00:03Z',
            },
          ],
          total: 1,
        }),
      })
      return
    }

    await route.fulfill({
      status: 404,
      json: envelope({ unexpected: `${method} ${path}` }),
    })
  })
}

async function main() {
  const failures = []
  const screenshots = []
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

  try {
    await mkdir(artifactDir, { recursive: true })
    await setupApiMocks(page)
    await page.goto(withQuery(targetUrl, { story: storyId }), { waitUntil: 'networkidle' })
    await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 15000 })
    await page.getByText(story.openingMessage).first().waitFor({ state: 'visible', timeout: 15000 })

    await saveScreenshot(page, screenshots, 'slice-c-focus-first-screen')

    const labels = await tabLabels(page)
    const expectedTabs = ['聚焦', 'AI助手', '证据', '配置']
    for (const label of expectedTabs) {
      if (!labels.includes(label)) failures.push(`Right workbench missing tab: ${label}; got ${labels.join(' / ')}`)
    }
    if (labels.includes('办理')) failures.push(`Right workbench must not include 办理 tab; got ${labels.join(' / ')}`)
    if (labels.join('|') !== expectedTabs.join('|')) {
      failures.push(`Right workbench tab order/count mismatch: expected ${expectedTabs.join(' / ')}, got ${labels.join(' / ')}`)
    }

    const focusPane = page.getByTestId('operator-workbench-focus-pane')
    for (const text of ['状态条', '业务对象摘要', 'SOP办理树', '风险与时效', '推荐回复', '高敏确认']) {
      await expectVisibleTextInFirstScreen(page, focusPane, text, failures)
    }

    if (await clickWorkbenchTab(page, 'AI助手', failures)) {
      const assistantPane = page.getByTestId('operator-workbench-assistant-pane')
      const assistantChatWindow = assistantPane.getByTestId('operator-assistant-chat-window')
      const assistantComposer = assistantPane.getByTestId('operator-assistant-chat-composer')
      if (!(await isVisible(assistantChatWindow, 1500))) failures.push('AI助手 tab must show a chat window')
      if (!(await isVisible(assistantComposer, 1500))) failures.push('AI助手 tab must show a chat composer')
      await saveScreenshot(page, screenshots, 'slice-c-ai-assistant-chat')

      await expectNoVisibleDescendant(assistantPane, 'operator-assistant-chat-header', failures, 'internal assistant header')
      await expectNoVisibleDescendant(assistantPane, 'operator-task-ledger', failures, 'task ledger')
      await expectNoVisibleDescendant(assistantPane, 'operator-worker-profile-config-panel', failures, 'worker config panel')
      await expectNoVisibleDescendant(assistantPane, 'operator-metrics-panel', failures, 'metrics panel')
      await expectNoVisibleDescendant(assistantPane, 'operator-eval-observability-panel', failures, 'eval metrics panel')

      const assistantText = await visibleText(assistantPane)
      for (const forbidden of ['任务台账', 'Worker 配置', '配置', '指标', '评估观测', '任务命中', '采纳率']) {
        if (assistantText.includes(forbidden)) {
          failures.push(`AI助手 pure chat must not expose "${forbidden}"`)
        }
      }
    }

    if (await clickWorkbenchTab(page, '证据', failures)) {
      const evidencePane = page.getByTestId('operator-workbench-evidence-pane')
      if (!(await isVisible(evidencePane, 1500))) failures.push('证据 tab did not open evidence debug pane')
      const evidenceText = await visibleText(evidencePane)
      if (!evidenceText.includes('评估观测') && !evidenceText.includes('识别证据') && !evidenceText.includes('操作审计')) {
        failures.push('证据 tab must expose debug evidence entries')
      }
      await saveScreenshot(page, screenshots, 'slice-c-evidence-debug-entry')
    }

    if (await clickWorkbenchTab(page, '配置', failures)) {
      const configPane = page.getByTestId('operator-workbench-config-pane')
      const workerConfigPanel = configPane.getByTestId('operator-worker-profile-config-panel')
      if (!(await isVisible(configPane, 1500))) failures.push('配置 tab did not open config debug pane')
      if (!(await isVisible(workerConfigPanel, 1500))) failures.push('配置 tab must expose worker config debug entry')
      const configText = await visibleText(configPane)
      if (!configText.includes('Worker 配置') || !configText.includes('refund_ticket_chatflow')) {
        failures.push('配置 tab must show worker config details')
      }
      await saveScreenshot(page, screenshots, 'slice-c-config-debug-entry')
    }

    if (failures.length > 0) {
      throw new Error(`Customer assistant AI workbench IA UAT failed:\n- ${failures.join('\n- ')}`)
    }

    await writeFile(
      notesPath,
      [
        '# Slice C Browser UAT',
        '',
        '- Result: PASS',
        `- URL: ${targetUrl}`,
        `- Tabs: ${expectedTabs.join(' / ')}`,
        '- Focus first screen: 状态条 / 业务对象摘要 / SOP办理树 / 风险与时效 / 推荐回复 / 高敏确认',
        '- AI助手: pure chat window without internal header, task ledger, config, or metrics surfaces',
        '- Debug entries: 证据 and 配置 tabs open',
        '',
        '## Screenshots',
        ...screenshots.map((path) => `- ${path}`),
        '',
      ].join('\n'),
    )

    console.log('PASS customer assistant AI workbench IA UAT')
    console.log(`Screenshots:\n${screenshots.join('\n')}`)
  } finally {
    await browser.close()
  }
}

await main()
