import { chromium } from 'playwright'

import { resolveFrontendServer } from './support/dev-server.mjs'

const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const storyId = 'refund_baggage_parallel'
const sessionId = 12
const taskId = 101
const actionId = 9
const runId = 31

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function envelope(data) {
  return { code: 200, message: 'success', data }
}

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function makeTask(status) {
  return {
    id: taskId,
    sessionId,
    taskKey: 'refund_ticket:MU5137-8899',
    taskType: 'REFUND',
    businessKey: 'refund_ticket',
    shortId: 'refund-101',
    status,
    workerType: 'chatflow_sop',
    workerRef: 'refund_ticket',
    checkpoint: { currentStep: 'collect_order_no' },
    lastResult: { status },
    proposedActions: [],
    version: 1,
  }
}

function makeAction(status, taskStatus) {
  return {
    id: actionId,
    sessionId,
    runId,
    taskId,
    actionKey: 'refund_ticket:cancel:MU5137-8899',
    actionType: 'PROPOSED_TASK_COMMAND',
    title: '确认任务变更：refund_ticket:MU5137-8899',
    payload: {
      taskCommand: {
        type: 'CANCEL_TASK',
        taskKey: 'refund_ticket',
        taskType: 'REFUND',
        businessKey: 'refund_ticket',
        workerType: 'chatflow_sop',
        workerRef: 'refund_ticket',
      },
    },
    status,
    result:
      status === 'CONFIRMED'
        ? {
            decision: { note: '客户已电话确认退票' },
            taskStatus,
          }
        : undefined,
  }
}

function makeOperatorAudit(status, taskStatus) {
  if (status !== 'CONFIRMED') return { sessionId, list: [], total: 0 }
  return {
    sessionId,
    list: [
      {
        id: 300,
        sequence: 2,
        eventType: 'proposed_task_command_confirmed',
        title: '任务变更已确认',
        actor: 'operator',
        source: 'operator_advisory',
        status: taskStatus,
        targetType: 'task',
        targetId: taskId,
        summary: '1 task command confirmed from the pending card',
        createdAt: '2026-06-20T00:00:00Z',
      },
    ],
    total: 1,
  }
}

async function main() {
  const server = await resolveFrontendServer()
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

  const story = {
    storyId,
    title: '退票 + 行李额并行',
    sessionId,
    sessionStatus: 'ACTIVE',
    customerName: '赵女士',
    maskedPhone: '138****0000',
    openingMessage: '我要退 MU5137 的票，也想确认行李额。',
    taskCount: 1,
    pendingActionCount: 1,
    knowledgeBaseIds: [201],
  }
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
  let taskStatus = 'RUNNING'
  let actionStatus = 'PENDING'
  let qaAnswered = false
  let eventRows = [
    {
      id: 1,
      sessionId,
      runId: 31,
      sequence: 1,
      type: 'run_started',
      visibility: 'normal',
      source: 'demo_seed',
      actor: 'system',
      taskId: null,
      parentSpanId: null,
      spanId: null,
      payload: { storyId },
      createdAt: '2026-06-20T00:00:00Z',
    },
  ]

  function makeStoryMetrics() {
    const currentEventCounts = eventRows.reduce(
      (counts, event) => {
        counts.byType[event.type] = (counts.byType[event.type] ?? 0) + 1
        counts.bySource[event.source] = (counts.bySource[event.source] ?? 0) + 1
        counts.total += 1
        return counts
      },
      { total: 0, byType: {}, bySource: {} },
    )

    return {
      storyCount: 1,
      sessionCount: 1,
      taskStatusCounts: taskStatus === 'CANCELLED' ? { CANCELLED: 1 } : { RUNNING: 1 },
      proposedActionStatusCounts: { [actionStatus]: 1 },
      humanConfirmation:
        actionStatus === 'CONFIRMED'
          ? { pending: 0, adopted: 1, terminal: 1, adoptionRate: 1 }
          : { pending: 1, adopted: 0, terminal: 0, adoptionRate: 0 },
      eventCounts: currentEventCounts,
      workerEventCounts: { total: 0, byType: {} },
      recentFailureReasons: [],
      stories: [
        {
          storyId,
          title: story.title,
          sessionId,
          sessionStatus: 'ACTIVE',
          taskCount: 1,
          pendingActionCount: 1,
          eventCount: currentEventCounts.total,
          workerEventCount: 0,
          taskStatusCounts: taskStatus === 'CANCELLED' ? { CANCELLED: 1 } : { RUNNING: 1 },
          proposedActionStatusCounts: { [actionStatus]: 1 },
          humanConfirmation:
            actionStatus === 'CONFIRMED'
              ? { pending: 0, adopted: 1, terminal: 1, adoptionRate: 1 }
              : { pending: 1, adopted: 0, terminal: 0, adoptionRate: 0 },
          eventCounts: currentEventCounts,
          workerEventCounts: { total: 0, byType: {} },
          recentFailureReasons: [],
        },
      ],
    }
  }

  async function fulfill(route, data) {
    await route.fulfill({ json: envelope(data) })
  }

  try {
    await page.route('**/api/v1/customer-assistant/**', async (route) => {
      const request = route.request()
      const url = request.url()
      const method = request.method()
      const body = request.postDataJSON?.()

      if (method === 'GET' && url.endsWith('/demo-stories')) {
        await fulfill(route, { list: [story], total: 1 })
        return
      }
      if (method === 'GET' && url.endsWith('/demo-stories/metrics')) {
        await fulfill(route, makeStoryMetrics())
        return
      }
      if (method === 'GET' && url.endsWith('/worker-profiles')) {
        await fulfill(route, workerProfiles)
        return
      }
      if (method === 'GET' && url.endsWith(`/sessions/${sessionId}/tasks`)) {
        await fulfill(route, { list: [makeTask(taskStatus)], total: 1 })
        return
      }
      if (method === 'GET' && url.endsWith(`/sessions/${sessionId}/proposed-actions`)) {
        await fulfill(route, { list: [makeAction(actionStatus, taskStatus)], total: 1 })
        return
      }
      if (method === 'GET' && url.endsWith(`/sessions/${sessionId}/events`)) {
        await fulfill(route, { list: clone(eventRows), total: eventRows.length })
        return
      }
      if (method === 'GET' && url.endsWith(`/sessions/${sessionId}/operator-audit`)) {
        await fulfill(route, makeOperatorAudit(actionStatus, taskStatus))
        return
      }
      if (method === 'GET' && url.endsWith(`/sessions/${sessionId}/metrics`)) {
        await fulfill(route, {
          sessionId,
          taskStatusCounts: taskStatus === 'CANCELLED' ? { CANCELLED: 1 } : { RUNNING: 1 },
          proposedActionStatusCounts: { [actionStatus]: 1 },
          humanConfirmation:
            actionStatus === 'CONFIRMED'
              ? { pending: 0, adopted: 1, terminal: 1, adoptionRate: 1 }
              : { pending: 1, adopted: 0, terminal: 0, adoptionRate: 0 },
          eventCounts: {
            total: eventRows.length,
            byType: eventRows.reduce((counts, event) => {
              counts[event.type] = (counts[event.type] ?? 0) + 1
              return counts
            }, {}),
            bySource: eventRows.reduce((counts, event) => {
              counts[event.source] = (counts[event.source] ?? 0) + 1
              return counts
            }, {}),
          },
          workerEventCounts: { total: 0, byType: {} },
          recentFailureReasons: [],
        })
        return
      }
      if (method === 'POST' && url.endsWith(`/sessions/${sessionId}/operator-knowledge-qa`)) {
        const question = String(body?.question || '').trim()
        if (question !== '退票和行李额可以并行处理吗？') {
          throw new Error(`Unexpected Q&A question: ${question}`)
        }
        qaAnswered = true
        eventRows = [
          ...eventRows,
          {
            id: 2,
            sessionId,
            runId: null,
            sequence: 2,
            type: 'operator_knowledge_qa_answered',
            visibility: 'normal',
            source: 'operator_advisory',
            actor: 'operator',
            taskId: null,
            parentSpanId: null,
            spanId: null,
            payload: { sourceCount: 1, evidenceCount: 1, warningCount: 0 },
            createdAt: '2026-06-20T00:00:01Z',
          },
        ]
        await fulfill(route, {
          sessionId,
          question,
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
              taskKey: 'refund_ticket',
              taskType: 'REFUND',
              status: taskStatus,
              workerType: 'chatflow_sop',
              workerRef: 'refund_ticket',
              currentStep: 'collect_order_no',
            },
          ],
          contextSummary: {
            sessionId,
            storyId,
            storyTitle: story.title,
            customer: { name: story.customerName, maskedPhone: story.maskedPhone },
            taskCount: 1,
            pendingActionCount: 1,
            eventCount: eventRows.length,
            knowledgeBaseIds: [201],
            latestEventTypes: eventRows.map((event) => event.type),
          },
          warnings: [],
        })
        return
      }
      if (method === 'POST' && url.endsWith(`/proposed-actions/${actionId}/confirm`)) {
        actionStatus = 'CONFIRMED'
        taskStatus = 'CANCELLED'
        eventRows = [
          ...eventRows,
          {
            id: 3,
            sessionId,
            runId: 31,
            sequence: 3,
            type: 'proposed_task_command_confirmed',
            visibility: 'normal',
            source: 'operator_advisory',
            actor: 'operator',
            taskId,
            parentSpanId: null,
            spanId: null,
            payload: { actionId, taskId },
            createdAt: '2026-06-20T00:00:02Z',
          },
        ]
        await fulfill(route, makeAction(actionStatus, taskStatus))
        return
      }

      await route.fulfill({ status: 404, json: { code: 404, message: 'unexpected call', data: null } })
    })

    await page.goto(`${server.baseUrl}/customer-assistant?story=${storyId}`, { waitUntil: 'networkidle' })
    await page.waitForFunction(
      () => document.body.innerText.includes('我要退 MU5137 的票，也想确认行李额。'),
      null,
      { timeout: 10000 },
    )

    const workbenchTabs = page.getByTestId('operator-ai-workbench-tabs')
    const tabLabels = await page.evaluate(() =>
      Array.from(document.querySelectorAll('[data-testid="operator-ai-workbench-tabs"] button')).map((button) =>
        button.textContent?.trim() || '',
      ),
    )
    assert(tabLabels.includes('聚焦'), `Expected focus tab label, got ${tabLabels.join(' / ')}`)
    assert(tabLabels.includes('AI助手'), `Expected assistant tab label, got ${tabLabels.join(' / ')}`)
    assert(tabLabels.includes('办理'), `Expected business handling tab label, got ${tabLabels.join(' / ')}`)
    assert(tabLabels.includes('证据'), `Expected evidence tab label, got ${tabLabels.join(' / ')}`)
    assert(tabLabels.includes('配置'), `Expected config tab label, got ${tabLabels.join(' / ')}`)
    for (const term of ['overview', 'tasks', 'evidence', 'audit']) {
      assert(!tabLabels.some((label) => label.includes(term)), `Expected non-technical tab labels only, found ${term}`)
    }
    assert(tabLabels[0] === '聚焦', `Expected focus tab to be first, got ${tabLabels.join(' / ')}`)

    async function clickWorkbenchTab(label) {
      await page.evaluate((targetLabel) => {
        const buttons = Array.from(document.querySelectorAll('[data-testid="operator-ai-workbench-tabs"] button'))
        const button = buttons.find((item) => item.textContent?.trim() === targetLabel)
        if (!button) throw new Error(`Missing workbench tab: ${targetLabel}`)
        button.click()
      }, label)
    }

    const shell = page.getByTestId('customer-assistant-three-column-shell')
    const shellBox = await shell.boundingBox()
    assert(shellBox, 'Expected three-column shell to be measurable')
    assert(shellBox.height <= 790, `Expected one-screen shell height, got ${shellBox.height}`)

    const leftColumn = page.getByTestId('customer-assistant-left-column')
    const centerColumn = page.getByTestId('customer-assistant-center-column')
    const workbenchColumn = page.getByTestId('customer-assistant-ai-workbench-column')
    for (const column of [leftColumn, centerColumn, workbenchColumn]) {
      const box = await column.boundingBox()
      assert(box, 'Expected column to be measurable')
      assert(box.height <= shellBox.height + 1, `Expected internal column fit, got ${box.height}`)
    }

    const focusPane = page.getByTestId('operator-workbench-focus-pane')
    await focusPane.getByTestId('operator-focus-intent-card').getByText('意图识别').waitFor({
      state: 'visible',
      timeout: 10000,
    })
    await focusPane.getByTestId('operator-focus-script-card').getByText('业务办理指引').waitFor({
      state: 'visible',
      timeout: 10000,
    })
    const focusConfirmationCards = focusPane.getByTestId('operator-confirmation-cards')
    await focusConfirmationCards.getByText('确认任务变更：refund_ticket:MU5137-8899').waitFor({
      state: 'visible',
      timeout: 10000,
    })
    const defaultFocusText = await focusPane.innerText()
    assert(defaultFocusText.includes('业务办理确认'), 'Expected default focus tab to show business confirmation')
    assert(!defaultFocusText.includes('Worker 配置'), 'Default focus tab should hide worker configuration')
    assert(!defaultFocusText.includes('modelPolicyRef'), 'Default focus tab should hide model policy refs')

    await clickWorkbenchTab('AI助手')
    const assistantPane = page.getByTestId('operator-workbench-assistant-pane')
    const qaPanel = assistantPane.getByTestId('operator-knowledge-qa-panel')
    await qaPanel.waitFor({ state: 'visible', timeout: 10000 })
    assert(!(await page.getByTestId('operator-worker-profile-config-panel').isVisible()), 'Worker config must be hidden before opening the config tab')
    await qaPanel.getByTestId('operator-knowledge-qa-question').fill('退票和行李额可以并行处理吗？')
    await qaPanel.getByRole('button', { name: '追问助手' }).click()
    await qaPanel.getByTestId('operator-knowledge-qa-answer').getByText('可以并行处理').waitFor({
      state: 'visible',
      timeout: 10000,
    })
    await qaPanel.getByTestId('operator-knowledge-qa-source').getByText('退票和行李额并行处理').waitFor({
      state: 'visible',
      timeout: 10000,
    })
    const qaText = await qaPanel.innerText()
    assert(qaText.includes('可以并行处理'), 'Expected assistant answer to be visible')
    assert(!qaText.includes('overview'), 'Assistant tab should not expose technical tab names')

    await clickWorkbenchTab('配置')
    const workerConfigPanel = page.getByTestId('operator-worker-profile-config-panel')
    await workerConfigPanel.waitFor({ state: 'visible', timeout: 10000 })
    const workerConfigText = await workerConfigPanel.innerText()
    assert(workerConfigText.includes('Worker 配置'), 'Expected worker config panel to be visible on config tab')
    assert(workerConfigText.includes('refund_ticket_chatflow'), 'Expected seeded worker profile in config tab')

    await clickWorkbenchTab('聚焦')
    const focusActionPanel = focusPane.getByTestId('operator-confirmation-cards')
    await focusActionPanel.getByText('确认任务变更：refund_ticket:MU5137-8899').waitFor({
      state: 'visible',
      timeout: 10000,
    })
    const actionRow = focusActionPanel.locator('.action-row').filter({ hasText: '确认任务变更：refund_ticket:MU5137-8899' }).first()
    await actionRow.getByLabel('确认拟议动作').click()
    await page.waitForFunction(
      () => {
        const row = Array.from(document.querySelectorAll('[data-testid="operator-workbench-focus-pane"] .action-row')).find((item) =>
          item.textContent?.includes('确认任务变更：refund_ticket:MU5137-8899'),
        )
        return row?.textContent?.includes('CONFIRMED')
      },
      null,
      { timeout: 10000 },
    )

    await clickWorkbenchTab('AI助手')
    const assistantActionPanel = assistantPane.getByTestId('operator-confirmation-cards')
    const assistantActionRow = assistantActionPanel.locator('.action-row').filter({
      hasText: '确认任务变更：refund_ticket:MU5137-8899',
    }).first()
    await page.waitForFunction(
      () => {
        const row = Array.from(document.querySelectorAll('[data-testid="operator-workbench-assistant-pane"] .action-row')).find((item) =>
          item.textContent?.includes('确认任务变更：refund_ticket:MU5137-8899'),
        )
        return row?.textContent?.includes('CONFIRMED')
      },
      null,
      { timeout: 10000 },
    )
    await assistantPane.getByTestId('operator-event-timeline').getByText('proposed_task_command_confirmed').waitFor({
      state: 'visible',
      timeout: 10000,
    })

    await clickWorkbenchTab('办理')
    const taskRow = page.getByTestId('operator-task-ledger').locator('.task-row').filter({
      hasText: 'refund_ticket:MU5137-8899',
    }).first()
    await taskRow.getByText('CANCELLED').waitFor({ state: 'visible', timeout: 10000 })

    await clickWorkbenchTab('证据')
    await page.getByTestId('operator-workbench-evidence-pane').getByTestId('operator-audit-panel').getByText('任务变更已确认').waitFor({
      state: 'visible',
      timeout: 10000,
    })

    const actionText = await assistantActionRow.innerText()
    assert(actionText.includes('CONFIRMED'), 'Expected confirmed card sync in proposed-actions panel')
    assert(actionText.includes('确认任务变更：refund_ticket:MU5137-8899'), 'Expected action title to remain stable')
    assert(qaAnswered, 'Expected the Q&A checkpoint to be exercised')

    if (screenshotPath) {
      await page.screenshot({ path: screenshotPath, fullPage: true })
    }

    console.log('PASS customer assistant final UAT checkpoints')
  } finally {
    await browser.close()
    await server.close()
  }
}

await main()
