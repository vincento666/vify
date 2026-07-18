import { chromium } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5174'
const outDir =
  process.env.HIFY_E2E_ARTIFACT_DIR ||
  'artifacts/slices/226-ai-assistant-runtime-convergence-shell/226.7'
const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const artifactDir = path.join(projectRoot, outDir)
const screenshotDir = path.join(artifactDir, 'screenshots')
const runDir = path.join(artifactDir, 'uat-runs')

const sessionId = 2267
const runId = 92267
const now = new Date().toISOString()
let releaseStream
let streamDelivered = false
const streamGate = new Promise((resolve) => {
  releaseStream = resolve
})

const run = {
  id: runId,
  sessionId,
  status: 'RUNNING',
  input: { message: '核对运行时、审批和子智能体状态' },
  result: {},
  startedAt: now,
  completedAt: null,
}

const plan = {
  id: `plan-${runId}`,
  planningStrategy: 'auto_lightweight',
  status: 'RUNNING',
  recognizedNeeds: ['核对执行状态', '保留审计引用'],
  steps: [
    { id: 'step:inspect', title: '检查运行时配置', status: 'RUNNING', toolName: 'read_workspace_file', sequence: 1 },
    { id: 'step:report', title: '汇总检查结果', status: 'PENDING', toolName: null, sequence: 2 },
  ],
  currentStep: {
    id: 'step:inspect',
    title: '检查运行时配置',
    status: 'RUNNING',
    toolName: 'read_workspace_file',
    sequence: 1,
  },
  plannedTools: ['read_workspace_file', 'update_customer_profile'],
}

const initialEvents = [
  event(1, 'run.started', 'RUNNING', '分析任务', '正在建立执行上下文。', {}, {
    activityId: 'phase:run',
  }),
  event(2, 'plan.step_started', 'RUNNING', '检查运行时配置', '正在核对持久化 worker 配置。', {
    step: { id: 'step:inspect', title: '检查运行时配置' },
  }, {
    activityId: `run:${runId}:step:step:inspect`,
    parentActivityId: 'phase:run',
  }),
  event(3, 'text.delta', 'RUNNING', '模型输出', '我先核对运行时配置，并同步检查权限记录。', {
    delta: '我先核对运行时配置，并同步检查权限记录。',
    streaming: true,
    source: 'openrouter_delta',
  }),
  event(4, 'tool.call_started', 'RUNNING', '读取配置文件', '正在读取 AGENTS.md。', {
    toolName: 'read_workspace_file',
    input: { path: 'AGENTS.md' },
  }, {
    activityId: 'tool-call:51',
    parentActivityId: `run:${runId}:step:step:inspect`,
  }, 51),
  event(5, 'tool.call_completed', 'COMPLETED', '读取配置文件', '已读取 AGENTS.md。', {
    toolName: 'read_workspace_file',
    output: { path: 'AGENTS.md', content: '# Hify Agent Guide' },
    status: 'COMPLETED',
  }, {
    activityId: 'tool-call:51',
    parentActivityId: `run:${runId}:step:step:inspect`,
  }, 51),
  event(6, 'approval.required', 'WAITING', '需要审批', '写入客户资料前需要操作员批准。', {
    approvalId: 12,
    toolName: 'update_customer_profile',
  }, {
    activityId: 'approval:12',
    parentActivityId: `run:${runId}:step:step:inspect`,
  }),
  event(7, 'tool.call_failed', 'FAILED', '知识库检索失败', '索引暂不可用，已保留错误审计。', {
    toolName: 'search_knowledge_base',
    status: 'FAILED',
    error: 'index unavailable',
  }, {
    activityId: 'tool-call:52',
    parentActivityId: `run:${runId}:step:step:inspect`,
  }, 52),
  event(8, 'subagent.execution_started', 'RUNNING', '客户资料核验', '正在核对客户与组织范围。', {
    executionId: 'customer-assistant-run-34',
    displayName: '客户资料核验',
    status: 'running',
    startedAt: now,
    statusRef: '/api/v1/customer-assistant/runs/34',
    eventStreamRef: '/api/v1/customer-assistant/sessions/12/events/stream',
    resultRef: '/api/v1/customer-assistant/runs/34',
  }, {
    activityId: 'subagent:customer-assistant-run-34',
    parentActivityId: `run:${runId}:step:step:inspect`,
  }),
  event(10, 'subagent.execution_completed', 'COMPLETED', '订单检查', '订单检查已完成。', {
    executionId: 'customer-assistant-run-33',
    displayName: '订单检查',
    status: 'completed',
    startedAt: now,
    completedAt: now,
    statusRef: '/api/v1/customer-assistant/runs/33',
    resultRef: '/api/v1/customer-assistant/runs/33',
  }, {
    activityId: 'subagent:customer-assistant-run-33',
    parentActivityId: `run:${runId}:step:step:inspect`,
  }),
]

const upsertEvent = event(9, 'tool.call_completed', 'COMPLETED', '读取配置文件', 'SSE 重连后确认读取结果。', {
  toolName: 'read_workspace_file',
  output: { path: 'AGENTS.md', content: '# Hify Agent Guide', replayed: true },
  status: 'COMPLETED',
}, {
  activityId: 'tool-call:51',
  parentActivityId: `run:${runId}:step:step:inspect`,
}, 51)

const inspector = {
  run,
  plan,
  activeTasks: [{
    id: `task-${runId}`,
    runId,
    planId: plan.id,
    planningStrategy: plan.planningStrategy,
    title: '核对运行时、审批和子智能体状态',
    status: 'RUNNING',
    phase: 'EXECUTE',
    currentTool: 'read_workspace_file',
    recognizedNeeds: plan.recognizedNeeds,
    plannedTools: plan.plannedTools,
    currentStep: plan.currentStep,
    updatedAt: now,
  }],
  toolCalls: [
    { id: 51, toolName: 'read_workspace_file', input: { path: 'AGENTS.md' }, output: {}, status: 'COMPLETED', durationMs: 420 },
    { id: 52, toolName: 'search_knowledge_base', input: {}, output: {}, status: 'FAILED', durationMs: 310 },
  ],
  approvalQueue: [{
    id: 12,
    sessionId,
    runId,
    toolName: 'update_customer_profile',
    riskLevel: 'HIGH',
    input: { customerId: 'customer-12' },
    status: 'PENDING',
  }],
  approvalHistory: [],
  recentErrors: [{ id: 7, title: '知识库检索失败', summary: '索引暂不可用。' }],
  eventTimeline: initialEvents.map((item) => ({
    id: item.id,
    sequence: item.sequence,
    type: item.type,
    status: item.status,
    level: item.level,
    title: item.visibleTitle,
    summary: item.visibleSummary,
    createdAt: item.createdAt,
  })),
  usage: {
    inputTokens: 1260,
    outputTokens: 184,
    totalTokens: 1444,
    elapsedMs: 8200,
    estimated: false,
  },
}

function event(
  sequence,
  type,
  status,
  visibleTitle,
  visibleSummary,
  payload = {},
  correlationIds = {},
  toolCallId = null,
) {
  return {
    id: sequence,
    sessionId,
    runId,
    taskId: null,
    toolCallId,
    sequence,
    type,
    level: status === 'FAILED' ? 'ERROR' : 'INFO',
    status,
    visibleTitle,
    visibleSummary,
    payload,
    correlationIds,
    createdAt: now,
  }
}

function envelope(data) {
  return { code: 200, message: 'OK', data }
}

async function fulfillJson(route, data) {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(envelope(data)),
  })
}

function sseFrame(item) {
  return `id: ${item.sequence}\nevent: ai_assistant_event\ndata: ${JSON.stringify(item)}\n\n`
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function isLightRgb(value) {
  const match = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
  if (!match) return false
  const [, red, green, blue] = match.map(Number)
  return (red + green + blue) / 3 >= 230
}

async function installRoutes(page) {
  await page.route('**/api/v1/ai-assistant/**', async (route) => {
    const url = new URL(route.request().url())
    const pathname = url.pathname
    const method = route.request().method()

    if (pathname.endsWith('/events/stream')) {
      if (!streamDelivered) {
        await streamGate
        streamDelivered = true
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: sseFrame(upsertEvent),
        })
        return
      }
      await route.fulfill({ status: 200, contentType: 'text/event-stream', body: ': keepalive\n\n' })
      return
    }

    if (method === 'GET' && pathname === '/api/v1/ai-assistant/sessions') {
      await fulfillJson(route, {
        list: [{ id: sessionId, title: 'Activity Shell UAT', status: 'ACTIVE', createdAt: now, updatedAt: now }],
        total: 1,
      })
      return
    }
    if (method === 'GET' && pathname === `/api/v1/ai-assistant/sessions/${sessionId}/runs`) {
      await fulfillJson(route, { list: [run], total: 1 })
      return
    }
    if (method === 'GET' && pathname === `/api/v1/ai-assistant/runs/${runId}/snapshot`) {
      await fulfillJson(route, {
        run,
        events: initialEvents,
        streamCursor: { lastSequence: 8 },
        inspector,
      })
      return
    }
    if (method === 'GET' && pathname === `/api/v1/ai-assistant/runs/${runId}/events`) {
      await fulfillJson(route, { list: initialEvents, total: initialEvents.length })
      return
    }
    if (method === 'GET' && pathname === `/api/v1/ai-assistant/runs/${runId}/inspector`) {
      await fulfillJson(route, inspector)
      return
    }
    await fulfillJson(route, { list: [], total: 0 })
  })
}

async function activityToggle(page, title) {
  const toggle = page.getByTestId('ai-assistant-activity-toggle').filter({ hasText: title })
  await toggle.waitFor({ state: 'visible', timeout: 10000 })
  return toggle
}

async function runUat() {
  fs.mkdirSync(screenshotDir, { recursive: true })
  fs.mkdirSync(runDir, { recursive: true })
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

  try {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await installRoutes(page)
    await page.goto(`${baseUrl}/ai-assistant`, { waitUntil: 'domcontentloaded' })
    await page.getByTestId('ai-assistant-shell').waitFor({ state: 'visible', timeout: 10000 })
    assert(
      (await page.getByTestId('ai-assistant-add-context').count()) === 0,
      'Inert Add Context control must not be rendered.',
    )
    await page.getByTestId('ai-assistant-activity-feed').waitFor({ state: 'visible', timeout: 10000 })
    await page.getByTestId('ai-assistant-assistant-message')
      .getByText('我先核对运行时配置，并同步检查权限记录。')
      .waitFor({ state: 'visible', timeout: 10000 })

    const runningToggle = await activityToggle(page, '检查运行时配置')
    const completedToggle = await activityToggle(page, '读取配置文件')
    const approvalToggle = await activityToggle(page, '需要审批')
    const failedToggle = await activityToggle(page, '知识库检索失败')
    assert(await runningToggle.getAttribute('aria-expanded') === 'true', 'running activity should default expanded')
    assert(await completedToggle.getAttribute('aria-expanded') === 'false', 'completed activity should auto collapse')
    assert(await approvalToggle.getAttribute('aria-expanded') === 'true', 'approval activity should stay expanded')
    assert(await failedToggle.getAttribute('aria-expanded') === 'true', 'failed activity should stay expanded')
    await page.getByTestId('ai-assistant-activity-progress').getByText('步骤 1/2').waitFor({
      state: 'visible',
      timeout: 10000,
    })
    await page.getByTestId('ai-assistant-activity-feed')
      .getByTestId('ai-assistant-approval-approve')
      .waitFor({ state: 'visible', timeout: 10000 })

    const subagentPresence = page.getByTestId('ai-assistant-subagent-presence')
    await subagentPresence.getByText('1 正在运行').waitFor({ state: 'visible', timeout: 10000 })
    const runningSubagent = page.getByTestId('ai-assistant-subagent-row').filter({ hasText: '客户资料核验' }).locator('button')
    const completedSubagent = page.getByTestId('ai-assistant-subagent-row').filter({ hasText: '订单检查' }).locator('button')
    assert(await runningSubagent.getAttribute('aria-expanded') === 'true', 'running subagent should show presence details')
    assert(await completedSubagent.getAttribute('aria-expanded') === 'false', 'completed subagent should collapse')

    await completedToggle.click()
    assert(await completedToggle.getAttribute('aria-expanded') === 'true', 'manual completed override should expand')
    releaseStream()
    for (let index = 0; index < 100 && !streamDelivered; index += 1) {
      await page.waitForTimeout(50)
    }
    assert(streamDelivered, 'stable activity SSE upsert was not delivered')
    await page.waitForTimeout(750)
    assert(
      await completedToggle.getAttribute('aria-expanded') === 'true',
      'manual override should survive stable activity SSE upsert and snapshot refresh',
    )
    const manualOverridePersisted = await completedToggle.getAttribute('aria-expanded')
    await completedToggle.click()
    assert(await completedToggle.getAttribute('aria-expanded') === 'false', 'completed activity should fold back to one line')

    const visualState = await page.evaluate(() => {
      const shell = document.querySelector('[data-testid="ai-assistant-shell"]')
      const feed = document.querySelector('[data-testid="ai-assistant-activity-feed"]')
      const spinner = document.querySelector('.ai-activity-row__spinner')
      return {
        shellBackground: shell ? getComputedStyle(shell).backgroundColor : '',
        feedBackground: feed ? getComputedStyle(feed).backgroundColor : '',
        reducedMotionAnimation: spinner ? getComputedStyle(spinner).animationName : '',
        activityCount: document.querySelectorAll('[data-testid="ai-assistant-activity-row"]').length,
        subagentCount: document.querySelectorAll('[data-testid="ai-assistant-subagent-row"]').length,
        overflowX: document.documentElement.scrollWidth - window.innerWidth,
        overflowY: document.documentElement.scrollHeight - window.innerHeight,
      }
    })
    assert(isLightRgb(visualState.shellBackground), `shell is not light: ${visualState.shellBackground}`)
    assert(isLightRgb(visualState.feedBackground), `activity feed is not light: ${visualState.feedBackground}`)
    assert(visualState.reducedMotionAnimation === 'none', `reduced motion spinner still animates: ${visualState.reducedMotionAnimation}`)
    assert(visualState.activityCount >= 5, `missing activity states: ${visualState.activityCount}`)
    assert(visualState.subagentCount === 2, `missing durable child presence rows: ${visualState.subagentCount}`)
    assert(visualState.overflowX <= 0, `horizontal overflow: ${visualState.overflowX}`)
    assert(visualState.overflowY <= 2, `page overflow: ${visualState.overflowY}`)

    const stream = page.getByTestId('ai-assistant-event-stream')
    await stream.evaluate((node) => {
      node.scrollTop = 0
    })
    const overviewScreenshot = path.join(screenshotDir, 'ai-assistant-light-activity-shell.png')
    await page.screenshot({ path: overviewScreenshot, fullPage: true })
    await stream.evaluate((node) => {
      node.scrollTop = node.scrollHeight
    })
    const exceptionScreenshot = path.join(screenshotDir, 'ai-assistant-approval-error-states.png')
    await page.screenshot({ path: exceptionScreenshot, fullPage: true })
    const report = {
      states: {
        runningExpanded: await runningToggle.getAttribute('aria-expanded'),
        completedManualOverridePersisted: manualOverridePersisted,
        completedFinalCollapsed: await completedToggle.getAttribute('aria-expanded'),
        approvalExpanded: await approvalToggle.getAttribute('aria-expanded'),
        failedExpanded: await failedToggle.getAttribute('aria-expanded'),
        activeSubagents: 1,
        completedSubagents: 1,
      },
      visualState,
      screenshots: [overviewScreenshot, exceptionScreenshot],
      verdict: 'PASS',
    }
    fs.writeFileSync(
      path.join(runDir, 'ai-assistant-activity-shell-uat.json'),
      JSON.stringify(report, null, 2),
    )
    console.log('PASS ai-assistant light activity shell browser uat')
  } finally {
    releaseStream()
    await browser.close()
  }
}

await runUat()
