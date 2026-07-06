import { chromium } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5174'
const outDir =
  process.env.HIFY_E2E_ARTIFACT_DIR ||
  'artifacts/slices/222-ai-assistant-general-harness-mvp/222.1'
const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const artifactDir = path.join(projectRoot, outDir)
const screenshotDir = path.join(artifactDir, 'screenshots')

const sessionId = 2221
const runId = 9001
const now = '2026-07-01T06:40:00Z'
let hasRun = false
let capturedRequest = null

const plan = {
  id: `plan-${runId}`,
  planningStrategy: 'auto_lightweight',
  status: 'COMPLETED',
  recognizedNeeds: ['展示一等计划状态', '调用只读工具', '回显最终结果'],
  steps: [
    {
      id: `plan-${runId}-step-1`,
      title: '读取工作区文件',
      status: 'COMPLETED',
      toolName: 'read_workspace_file',
      sequence: 1,
    },
  ],
  currentStep: {
    id: `plan-${runId}-step-1`,
    title: '读取工作区文件',
    status: 'COMPLETED',
    toolName: 'read_workspace_file',
    sequence: 1,
  },
  plannedTools: ['read_workspace_file'],
  finalResult: '已完成计划执行并返回结果。',
}

const run = {
  id: runId,
  sessionId,
  status: 'COMPLETED',
  input: {
    message: '请读取 AGENTS.md 并展示计划',
    planningStrategy: 'auto_lightweight',
    plan,
  },
  result: {
    finalAnswer: '已读取 AGENTS.md，并完成计划任务。',
    plan,
  },
  startedAt: now,
  completedAt: now,
}

const events = [
  event(1, 'run.started', 'RUNNING', '任务已开始', 'AI Assistant 开始处理请求。'),
  event(2, 'plan.created', 'PENDING', '计划已创建', '已识别需求并生成 1 个步骤。'),
  event(3, 'task.created', 'PENDING', '任务已登记', '任务面板可回显计划。'),
  event(4, 'plan.step_started', 'RUNNING', '步骤开始', '读取工作区文件。'),
  event(5, 'task.updated', 'RUNNING', '任务已更新', '任务面板已同步当前计划进度。'),
  event(6, 'tool.call_started', 'RUNNING', '工具调用开始', '读取工作区文件。'),
  event(7, 'tool.call_completed', 'COMPLETED', '工具调用完成', '读取工作区文件完成。'),
  event(8, 'plan.step_completed', 'COMPLETED', '步骤完成', '读取工作区文件完成。'),
  event(9, 'task.updated', 'COMPLETED', '任务已更新', '任务面板已同步当前计划进度。'),
  event(10, 'task.completed', 'COMPLETED', '任务完成', '计划任务已完成。'),
  event(11, 'run.completed', 'COMPLETED', '最终结果', '已读取 AGENTS.md，并完成计划任务。'),
]

const inspector = {
  run,
  plan,
  activeTasks: [
    {
      id: `task-${runId}`,
      runId,
      planId: plan.id,
      planningStrategy: plan.planningStrategy,
      title: '请读取 AGENTS.md 并展示计划',
      status: 'COMPLETED',
      phase: 'FINALIZE',
      currentTool: 'read_workspace_file',
      recognizedNeeds: plan.recognizedNeeds,
      plannedTools: plan.plannedTools,
      currentStep: plan.currentStep,
      finalResult: plan.finalResult,
      updatedAt: now,
    },
  ],
  toolCalls: [
    {
      id: 7001,
      toolName: 'read_workspace_file',
      input: { path: 'AGENTS.md' },
      output: { content: '# AGENTS.md' },
      status: 'COMPLETED',
      durationMs: 12,
    },
  ],
  approvalQueue: [],
  approvalHistory: [],
  recentErrors: [],
  eventTimeline: events.map((item) => ({
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
    inputTokens: 120,
    outputTokens: 48,
    totalTokens: 168,
    elapsedMs: 320,
    estimated: true,
  },
}

function event(sequence, type, status, visibleTitle, visibleSummary) {
  return {
    id: sequence,
    sessionId,
    runId,
    taskId: null,
    toolCallId: null,
    sequence,
    type,
    level: 'INFO',
    status,
    visibleTitle,
    visibleSummary,
    payload: type.startsWith('plan.')
      ? { planId: plan.id, planningStrategy: plan.planningStrategy }
      : {},
    correlationIds: {},
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

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function installRoutes(page) {
  await page.route('**/api/v1/ai-assistant/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const pathname = url.pathname
    const method = request.method()

    if (pathname.endsWith('/events/stream')) {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: `event: ai_assistant_event\ndata: ${JSON.stringify(events[events.length - 1])}\n\n`,
      })
      return
    }

    if (method === 'GET' && pathname === '/api/v1/ai-assistant/sessions') {
      await fulfillJson(route, {
        list: hasRun ? [{ id: sessionId, title: 'UAT', status: 'ACTIVE', createdAt: now, updatedAt: now }] : [],
        total: hasRun ? 1 : 0,
      })
      return
    }

    if (method === 'POST' && pathname === '/api/v1/ai-assistant/sessions') {
      await fulfillJson(route, { id: sessionId, title: 'UAT', status: 'ACTIVE', createdAt: now, updatedAt: now })
      return
    }

    if (method === 'GET' && pathname === `/api/v1/ai-assistant/sessions/${sessionId}/runs`) {
      await fulfillJson(route, { list: hasRun ? [run] : [], total: hasRun ? 1 : 0 })
      return
    }

    if (method === 'POST' && pathname === `/api/v1/ai-assistant/sessions/${sessionId}/messages/async`) {
      capturedRequest = JSON.parse(request.postData() || '{}')
      hasRun = true
      await fulfillJson(route, {
        runId,
        sessionId,
        status: 'COMPLETED',
        replayed: false,
        planningStrategy: plan.planningStrategy,
        plan,
        finalAnswer: run.result.finalAnswer,
        toolCalls: inspector.toolCalls,
        eventStreamRef: `/api/v1/ai-assistant/runs/${runId}/events/stream?afterSequence=0`,
      })
      return
    }

    if (method === 'GET' && pathname === `/api/v1/ai-assistant/runs/${runId}/events`) {
      await fulfillJson(route, { list: events, total: events.length })
      return
    }

    if (method === 'GET' && pathname === `/api/v1/ai-assistant/runs/${runId}/inspector`) {
      await fulfillJson(route, inspector)
      return
    }

    await fulfillJson(route, { list: [], total: 0 })
  })
}

async function runUat() {
  fs.mkdirSync(screenshotDir, { recursive: true })
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

  try {
    await installRoutes(page)
    await page.goto(`${baseUrl}/ai-assistant`, { waitUntil: 'networkidle' })
    await page.getByTestId('ai-assistant-shell').waitFor({ state: 'visible', timeout: 10000 })
    await page.getByPlaceholder('输入给 AI 助手的消息').fill('请读取 AGENTS.md 并展示计划')
    await page.getByTestId('ai-assistant-send').click()
    await page.getByTestId('ai-assistant-plan-panel').waitFor({ state: 'visible', timeout: 10000 })
    await page.getByTestId('ai-assistant-final-result').getByText(plan.finalResult).waitFor({ timeout: 10000 })

    const state = await page.evaluate(() => {
      const text = (testId) => document.querySelector(`[data-testid="${testId}"]`)?.textContent?.trim() || ''
      const list = (testId) =>
        Array.from(document.querySelectorAll(`[data-testid="${testId}"]`)).map((node) => node.textContent?.trim() || '')
      return {
        planningStrategy: text('ai-assistant-planning-strategy'),
        recognizedNeeds: text('ai-assistant-recognized-needs'),
        plannedSteps: list('ai-assistant-planned-step'),
        activeStep: text('ai-assistant-active-step'),
        currentTool: text('ai-assistant-current-tool'),
        finalResult: text('ai-assistant-final-result'),
        taskRows: list('ai-assistant-task-row'),
        finalAnswers: list('ai-assistant-run-final-answer'),
      }
    })

    assert(capturedRequest?.planningStrategy === 'auto_lightweight', `unexpected planning strategy ${capturedRequest?.planningStrategy}`)
    assert(state.planningStrategy.includes('自动轻量规划'), `missing strategy label: ${state.planningStrategy}`)
    assert(state.recognizedNeeds.includes('展示一等计划状态'), `missing recognized needs: ${state.recognizedNeeds}`)
    assert(state.plannedSteps.some((step) => step.includes('读取工作区文件')), `missing planned step: ${state.plannedSteps.join(' | ')}`)
    assert(state.activeStep.includes('读取工作区文件'), `missing active step: ${state.activeStep}`)
    assert(state.currentTool.includes('读取工作区文件'), `missing current tool: ${state.currentTool}`)
    assert(state.finalResult.includes(plan.finalResult), `missing final result: ${state.finalResult}`)
    assert(state.taskRows.some((row) => row.includes('FINALIZE')), `missing task row phase: ${state.taskRows.join(' | ')}`)

    const screenshot = path.join(screenshotDir, 'ai-assistant-plan-task-uat.png')
    await page.screenshot({ path: screenshot, fullPage: true })
    fs.writeFileSync(
      path.join(artifactDir, 'ai-assistant-plan-task-uat.json'),
      JSON.stringify({ capturedRequest, state, screenshot }, null, 2),
    )
    console.log('PASS ai-assistant plan/task browser uat')
  } finally {
    await browser.close()
  }
}

await runUat()
