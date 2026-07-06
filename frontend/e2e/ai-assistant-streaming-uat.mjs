import { chromium } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5174'
const outDir =
  process.env.HIFY_E2E_ARTIFACT_DIR ||
  'artifacts/slices/222-ai-assistant-general-harness-mvp/222.2'
const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const artifactDir = path.join(projectRoot, outDir)
const screenshotDir = path.join(artifactDir, 'screenshots')
const runDir = path.join(artifactDir, 'uat-runs')

const sessionId = 2222
const runId = 9102
const now = '2026-07-01T08:10:00Z'
let hasRun = false
let capturedRequest = null
const streamAfterSequences = []
let snapshotRequests = 0

const plan = {
  id: `plan-${runId}`,
  planningStrategy: 'auto_lightweight',
  status: 'COMPLETED',
  recognizedNeeds: ['验证 token 级实时输出', '验证断线后按 sequence 续传'],
  steps: [
    {
      id: `plan-${runId}-step-1`,
      title: '实时输出模型文本',
      status: 'COMPLETED',
      toolName: null,
      sequence: 1,
    },
  ],
  currentStep: {
    id: `plan-${runId}-step-1`,
    title: '实时输出模型文本',
    status: 'COMPLETED',
    toolName: null,
    sequence: 1,
  },
  plannedTools: [],
  finalResult: '实时输出完成。',
}

const run = {
  id: runId,
  sessionId,
  status: 'COMPLETED',
  input: { message: '请实时输出两个 token', planningStrategy: 'auto_lightweight', plan },
  result: { finalAnswer: '实时输出完成。', plan },
  startedAt: now,
  completedAt: now,
}

const initialEvents = [
  event(1, 'run.started', 'RUNNING', '运行开始', 'AI Assistant 开始处理请求。'),
  event(2, 'plan.created', 'COMPLETED', '计划已创建', '已识别实时输出需求。', { plan }),
  event(3, 'task.created', 'COMPLETED', '任务已创建', '任务面板已绑定结构化计划。'),
  event(4, 'model.call_started', 'RUNNING', '模型调用开始', '正在调用 streaming provider。'),
  event(5, 'task.updated', 'RUNNING', '任务编排', '任务面板已记录实时输出状态。', {
    phase: 'live_model_planning',
    toolNames: [],
  }),
]

const streamEvents = [
  event(6, 'text.delta', 'RUNNING', '实时输出', '实时', {
    delta: '实时',
    chunk: '实时',
    source: 'openrouter_delta',
    streaming: true,
  }),
  event(7, 'text.delta', 'RUNNING', '实时输出', '输出', {
    delta: '输出',
    chunk: '输出',
    source: 'openrouter_delta',
    streaming: true,
  }),
  event(8, 'run.completed', 'COMPLETED', '运行完成', '实时输出完成。', {
    finalAnswer: '实时输出完成。',
  }),
]

const allEvents = [...initialEvents, ...streamEvents]

const inspector = {
  run,
  plan,
  activeTasks: [
    {
      id: `task-${runId}`,
      runId,
      planId: plan.id,
      planningStrategy: plan.planningStrategy,
      title: '请实时输出两个 token',
      status: 'COMPLETED',
      phase: 'FINALIZE',
      currentTool: null,
      recognizedNeeds: plan.recognizedNeeds,
      plannedTools: plan.plannedTools,
      currentStep: plan.currentStep,
      finalResult: plan.finalResult,
      updatedAt: now,
    },
  ],
  toolCalls: [],
  approvalQueue: [],
  approvalHistory: [],
  recentErrors: [],
  eventTimeline: allEvents.map((item) => ({
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
    inputTokens: 88,
    outputTokens: 2,
    totalTokens: 90,
    elapsedMs: 180,
    estimated: false,
  },
}

function event(sequence, type, status, visibleTitle, visibleSummary, payload = {}) {
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
    payload,
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

function sseFrame(item) {
  return `id: ${item.sequence}\nevent: ai_assistant_event\ndata: ${JSON.stringify(item)}\n\n`
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
      const afterSequence = Number(url.searchParams.get('afterSequence') || 0)
      streamAfterSequences.push(afterSequence)
      const body =
        afterSequence < 6
          ? sseFrame(streamEvents[0])
          : `${sseFrame(streamEvents[1])}${sseFrame(streamEvents[2])}`
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body,
      })
      return
    }

    if (method === 'GET' && pathname === '/api/v1/ai-assistant/sessions') {
      await fulfillJson(route, {
        list: hasRun ? [{ id: sessionId, title: 'Streaming UAT', status: 'ACTIVE', createdAt: now, updatedAt: now }] : [],
        total: hasRun ? 1 : 0,
      })
      return
    }

    if (method === 'POST' && pathname === '/api/v1/ai-assistant/sessions') {
      await fulfillJson(route, { id: sessionId, title: 'Streaming UAT', status: 'ACTIVE', createdAt: now, updatedAt: now })
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
        status: 'RUNNING',
        replayed: false,
        planningStrategy: plan.planningStrategy,
        plan,
        finalAnswer: '',
        toolCalls: [],
        eventStreamRef: `/api/v1/ai-assistant/runs/${runId}/events/stream?afterSequence=0`,
      })
      return
    }

    if (method === 'GET' && pathname === `/api/v1/ai-assistant/runs/${runId}/events`) {
      await fulfillJson(route, { list: hasRun ? initialEvents : [], total: hasRun ? initialEvents.length : 0 })
      return
    }

    if (method === 'GET' && pathname === `/api/v1/ai-assistant/runs/${runId}/snapshot`) {
      snapshotRequests += 1
      await fulfillJson(route, {
        run,
        events: initialEvents,
        streamCursor: { lastSequence: initialEvents[initialEvents.length - 1].sequence },
        inspector,
      })
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
  fs.mkdirSync(runDir, { recursive: true })
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

  try {
    await installRoutes(page)
    await page.goto(`${baseUrl}/ai-assistant`, { waitUntil: 'networkidle' })
    await page.getByTestId('ai-assistant-shell').waitFor({ state: 'visible', timeout: 10000 })
    await page.getByPlaceholder('输入给 AI 助手的消息').fill('请实时输出两个 token')
    await page.getByTestId('ai-assistant-send').click()
    await page.getByTestId('ai-assistant-assistant-message').getByText('实时输出').waitFor({ timeout: 10000 })
    await page.getByTestId('ai-assistant-run-final-answer').getByText('实时输出完成。').waitFor({ timeout: 10000 })

    const state = await page.evaluate(() => {
      const list = (testId) =>
        Array.from(document.querySelectorAll(`[data-testid="${testId}"]`)).map((node) => node.textContent?.trim() || '')
      return {
        assistantMessages: list('ai-assistant-assistant-message'),
        finalAnswers: list('ai-assistant-run-final-answer'),
        taskRows: list('ai-assistant-task-row'),
      }
    })

    assert(capturedRequest?.modelMode === 'live', `unexpected modelMode ${capturedRequest?.modelMode}`)
    assert(snapshotRequests > 0, 'frontend did not call run snapshot recovery endpoint')
    assert(streamAfterSequences[0] === 5, `first stream did not resume from snapshot cursor: ${streamAfterSequences.join(',')}`)
    assert(streamAfterSequences.some((value) => value >= 6), `stream did not reconnect after delta: ${streamAfterSequences.join(',')}`)
    assert(state.assistantMessages.some((text) => text.includes('实时输出')), `missing streamed assistant text: ${state.assistantMessages.join(' | ')}`)
    assert(state.finalAnswers.some((text) => text.includes('实时输出完成。')), `missing final answer: ${state.finalAnswers.join(' | ')}`)
    assert(state.taskRows.some((text) => text.includes('FINALIZE')), `missing finalized task row: ${state.taskRows.join(' | ')}`)

    const screenshot = path.join(screenshotDir, 'ai-assistant-streaming-uat.png')
    await page.screenshot({ path: screenshot, fullPage: true })
    const report = {
      capturedRequest,
      snapshotRequests,
      streamAfterSequences,
      state,
      screenshot,
      verdict: 'PASS',
    }
    fs.writeFileSync(path.join(runDir, 'ai-assistant-streaming-uat.json'), JSON.stringify(report, null, 2))
    fs.writeFileSync(
      path.join(artifactDir, 'uat.md'),
      [
        '# UAT',
        '',
        '- Spec: 222-ai-assistant-general-harness-mvp',
        '- Slice: 222.2 StreamingRuntime',
        `- URL: ${baseUrl}/ai-assistant`,
        '- Browser: Playwright Chromium',
        '- Steps: send a mocked live request, receive one text.delta, reconnect with afterSequence, receive the next text.delta and terminal event.',
        '- Expected: token delta text renders incrementally and final answer recovers after reconnect.',
        `- Actual: ${JSON.stringify({ snapshotRequests, streamAfterSequences, assistantMessages: state.assistantMessages, finalAnswers: state.finalAnswers })}`,
        `- Screenshots: ${screenshot}`,
        '- Verdict: PASS',
        '',
      ].join('\n'),
    )
    console.log('PASS ai-assistant streaming browser uat')
  } finally {
    await browser.close()
  }
}

await runUat()
