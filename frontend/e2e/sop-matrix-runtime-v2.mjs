import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const artifactDir = process.env.HIFY_E2E_ARTIFACT_DIR
  || resolve(process.cwd(), 'artifacts/slices/216-chatflow-sop-compat-on-dag/216.4')
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || join(artifactDir, 'screenshots')
const reportPath = process.env.HIFY_E2E_REPORT || join(artifactDir, 'sop-matrix-runtime-v2.json')
const manifestPath = resolve(process.cwd(), 'frontend/e2e/fixtures/sop-matrix/runtime-v2-12-case-matrix.json')
const mirrorKeys = new Set([
  'currentStep',
  'pendingPrompt',
  'collected',
  'scopedVariables',
  'checkpoint',
  'checkpointId',
  'nodeEvents',
  'runStatus',
  'businessRefs',
])

const manifest = JSON.parse(await readFile(manifestPath, 'utf8'))
const caseById = new Map(manifest.cases.map((item) => [item.id, item]))

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function withParam(path, key, value) {
  return `${path}${path.includes('?') ? '&' : '?'}${key}=${encodeURIComponent(value)}`
}

async function unwrap(response, label) {
  const text = await response.text()
  let payload = {}
  try {
    payload = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`${label} returned non-JSON HTTP ${response.status()}: ${text}`)
  }
  assert(response.ok(), `${label} HTTP ${response.status()}: ${text}`)
  assert(payload.code === 200, `${label} API ${payload.message || text}`)
  return payload.data
}

async function getJson(page, path, label) {
  return unwrap(await page.request.get(`${baseUrl}${path}`), label)
}

async function getSseFrame(page, path, label) {
  const response = await page.request.get(`${baseUrl}${path}`, {
    headers: { Accept: 'text/event-stream' },
  })
  const text = await response.text()
  assert(response.ok(), `${label} HTTP ${response.status()}: ${text}`)
  const dataLine = text.split('\n').find((line) => line.startsWith('data:'))
  assert(dataLine, `${label} should return an SSE data frame: ${text}`)
  return JSON.parse(dataLine.slice('data:'.length).trim())
}

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const consoleErrors = []
const failedResponses = []

page.on('console', (message) => {
  if (message.type() === 'error') consoleErrors.push(message.text())
})
page.on('response', (response) => {
  if (response.url().includes('/api/') && response.status() >= 400) {
    failedResponses.push(`${response.status()} ${response.url()}`)
  }
})

try {
  await mkdir(screenshotDir, { recursive: true })
  await page.goto(`${baseUrl}/runtime-lab/chat`, { waitUntil: 'networkidle' })
  await page.getByTestId('runtime-lab-chat').waitFor({ timeout: 15_000 })

  const records = []

  records.push(await caseStrongIntentStart())
  records.push(await caseActiveSopContinue())
  const switchContext = await runSwitchJourney()
  records.push(switchContext.records.get('interruptible-switch'))
  records.push(switchContext.records.get('resume-offer-after-new-sop-complete'))
  records.push(switchContext.records.get('resume-original-child-run'))
  records.push(await caseNonInterruptibleSwitchRejected())
  records.push(await caseExplicitResumeSignal())
  records.push(await caseClarifyDoesNotCreateRun())
  records.push(await caseFaqNoStatePollution())
  records.push(await caseAgentFallbackNoStateReplacement())
  records.push(await caseHandoffPreservesRuntimeRefs())
  records.push(switchContext.records.get('multiple-child-runs-aggregate-only'))

  for (const record of records) {
    assert(record, 'matrix record should exist')
    assert(caseById.has(record.id), `unexpected case id ${record.id}`)
    assert(record.evidence.apiResponse, `${record.id} missing apiResponse evidence`)
    assert(record.evidence.eventStream, `${record.id} missing eventStream evidence`)
    assert(record.evidence.taskPanel, `${record.id} missing taskPanel evidence`)
    assert(record.evidence.refreshRecovery, `${record.id} missing refreshRecovery evidence`)
  }
  assert(new Set(records.map((record) => record.id)).size === manifest.cases.length, 'matrix should cover every case exactly once')
  assert(failedResponses.length === 0, `Failed API responses: ${failedResponses.join(' | ')}`)

  await writeFile(
    reportPath,
    `${JSON.stringify({
      schema: manifest.schema,
      baseUrl,
      cases: records,
      consoleErrors,
      failedResponses,
    }, null, 2)}\n`,
  )
  console.log(`PASS SOP runtime v2 matrix ${records.length} cases report=${reportPath}`)
} finally {
  await browser.close()
}

async function caseStrongIntentStart() {
  const sessionId = await createFreshSession()
  await sendTurn('我要退票')
  await waitForRouteAction('START_SOP')
  await expectTaskStatus('refund_ticket', 'RUNNING')
  const evidence = await collectEvidence('strong-intent-start', sessionId, {
    expectedTasks: [{ sopId: 'refund_ticket', status: 'RUNNING' }],
    requireRun: true,
  })
  const refund = evidence.apiResponse.tasks.list.find((task) => task.sopId === 'refund_ticket')
  assert(refund?.chatflowSession?.runId > 0, 'strong intent should expose child run refs')
  return evidence
}

async function caseActiveSopContinue() {
  const sessionId = await createFreshSession()
  await sendTurn('我要退票')
  await waitForRouteAction('START_SOP')
  await sendTurn('订单号 TK216401，手机号 13800138401，乘机人张矩阵')
  await waitForAnyRouteAction(['CONTINUE_ACTIVE_SOP', 'COMPLETE_TASK'])
  await expectTaskStatus('refund_ticket', 'RUNNING')
  return collectEvidence('active-sop-continue', sessionId, {
    expectedTasks: [{ sopId: 'refund_ticket', status: 'RUNNING' }],
    requireRun: true,
  })
}

async function runSwitchJourney({ resumeMessage = '继续处理退票', captureRecords = true } = {}) {
  const records = new Map()
  const sessionId = await createFreshSession()
  await sendTurn('我要退票')
  await waitForRouteAction('START_SOP')
  const beforeSwitch = await getTraceTask(sessionId, 'refund_ticket')
  const originalRunId = beforeSwitch.chatflow.runId

  await sendTurn('我要开发票')
  await waitForRouteAction('SUSPEND_AND_START')
  await expectTaskStatus('refund_ticket', 'SUSPENDED')
  await expectTaskStatus('invoice_apply', 'RUNNING')
  if (captureRecords) {
    records.set('interruptible-switch', await collectEvidence('interruptible-switch', sessionId, {
      expectedTasks: [
        { sopId: 'refund_ticket', status: 'SUSPENDED' },
        { sopId: 'invoice_apply', status: 'RUNNING' },
      ],
      requireRun: true,
    }))
  }

  await sendTurn('订单号 INV2164，手机号 13800138402，乘机人王矩阵')
  await waitForRouteAction('CONTINUE_ACTIVE_SOP')
  await sendTurn('发票抬头：Hify 科技')
  await waitForRouteAction('CONTINUE_ACTIVE_SOP')
  await sendTurn('确认')
  await waitForRouteAction('COMPLETE_TASK')
  await expectTaskStatus('invoice_apply', 'COMPLETED')
  if (captureRecords) {
    records.set('resume-offer-after-new-sop-complete', await collectEvidence('resume-offer-after-new-sop-complete', sessionId, {
      expectedTasks: [
        { sopId: 'refund_ticket', status: 'SUSPENDED' },
        { sopId: 'invoice_apply', status: 'COMPLETED' },
      ],
      requireResumeOffer: true,
      requireRun: true,
    }))
  }

  await sendTurn(resumeMessage)
  await waitForRouteAction('RESUME_TASK')
  await expectTaskStatus('refund_ticket', 'RUNNING')
  const resumedTrace = await getTraceTask(sessionId, 'refund_ticket')
  assert(resumedTrace.chatflow.runId === originalRunId, `resume should keep original run ${originalRunId}, got ${resumedTrace.chatflow.runId}`)
  if (captureRecords) {
    records.set('resume-original-child-run', await collectEvidence('resume-original-child-run', sessionId, {
      expectedTasks: [
        { sopId: 'refund_ticket', status: 'RUNNING' },
        { sopId: 'invoice_apply', status: 'COMPLETED' },
      ],
      requireRun: true,
    }))

    records.set('multiple-child-runs-aggregate-only', await collectEvidence('multiple-child-runs-aggregate-only', sessionId, {
      expectedTasks: [
        { sopId: 'refund_ticket', status: 'RUNNING' },
        { sopId: 'invoice_apply', status: 'COMPLETED' },
      ],
      requireMultipleRuns: true,
      requireRun: true,
    }))
  }
  return { sessionId, records }
}

async function caseNonInterruptibleSwitchRejected() {
  const sessionId = await createFreshSession()
  await sendTurn('我要退票')
  await waitForRouteAction('START_SOP')
  await sendTurn('订单号 TK216402，手机号 13800138403，乘机人李矩阵')
  await waitForRouteAction('CONTINUE_ACTIVE_SOP')
  await sendTurn('我要改签')
  await waitForRouteAction('REJECT_SWITCH_CONTINUE_ACTIVE')
  await expectTaskStatus('refund_ticket', 'RUNNING')
  return collectEvidence('non-interruptible-switch-rejected', sessionId, {
    expectedTasks: [{ sopId: 'refund_ticket', status: 'RUNNING' }],
    requireRun: true,
  })
}

async function caseExplicitResumeSignal() {
  const context = await runSwitchJourney({ resumeMessage: '恢复之前的退票', captureRecords: false })
  return collectEvidence('explicit-resume-signal', context.sessionId, {
    expectedTasks: [
      { sopId: 'refund_ticket', status: 'RUNNING' },
      { sopId: 'invoice_apply', status: 'COMPLETED' },
    ],
    requireRun: true,
  })
}

async function caseClarifyDoesNotCreateRun() {
  const sessionId = await createFreshSession()
  await sendTurn('你好')
  await waitForRouteAction('CLARIFY')
  return collectEvidence('clarify-does-not-create-run', sessionId, {
    expectedTasks: [],
    expectNoRuns: true,
  })
}

async function caseFaqNoStatePollution() {
  const sessionId = await createFreshSession()
  await sendTurn('我要退票')
  await waitForRouteAction('START_SOP')
  const before = await getTraceTask(sessionId, 'refund_ticket')
  await sendTurn('儿童票可以退吗？')
  await waitForAnyRouteAction(['ANSWER_FAQ', 'ANSWER_RAG'])
  const after = await getTraceTask(sessionId, 'refund_ticket')
  assert(after.chatflow.runId === before.chatflow.runId, 'FAQ/RAG should preserve child run id')
  return collectEvidence('faq-rag-no-state-pollution', sessionId, {
    expectedTasks: [{ sopId: 'refund_ticket', status: 'RUNNING' }],
    requireRun: true,
  })
}

async function caseAgentFallbackNoStateReplacement() {
  const sessionId = await createFreshSession()
  await sendTurn('我要退票')
  await waitForRouteAction('START_SOP')
  await sendTurn('订单号 TK216403，手机号 13800138404，乘机人赵矩阵')
  await waitForRouteAction('CONTINUE_ACTIVE_SOP')
  await sendTurn('确认')
  await waitForRouteAction('COMPLETE_TASK')
  await sendTurn('机场大巴末班车几点')
  await waitForLedgerAction(sessionId, 'AGENT_FALLBACK')
  return collectEvidence('agent-fallback-no-state-replacement', sessionId, {
    expectedTasks: [{ sopId: 'refund_ticket', status: 'COMPLETED' }],
    requiredLedgerAction: 'AGENT_FALLBACK',
    requireRun: true,
  })
}

async function caseHandoffPreservesRuntimeRefs() {
  const sessionId = await createFreshSession()
  await sendTurn('我要退票')
  await waitForRouteAction('START_SOP')
  const before = await getTraceTask(sessionId, 'refund_ticket')
  await sendTurn('我要转人工客服')
  await waitForRouteAction('HANDOFF_TO_HUMAN')
  const after = await getTraceTask(sessionId, 'refund_ticket')
  assert(after.chatflow.runId === before.chatflow.runId, 'handoff should preserve child run id')
  return collectEvidence('handoff-preserves-runtime-refs', sessionId, {
    expectedTasks: [{ sopId: 'refund_ticket', status: 'RUNNING' }],
    requireRun: true,
  })
}

async function collectEvidence(caseId, sessionId, options = {}) {
  const manifestCase = caseById.get(caseId)
  assert(manifestCase, `missing manifest case ${caseId}`)
  const tasks = await getJson(page, `/api/v1/runtime-lab/sessions/${sessionId}/tasks`, `${caseId} tasks`)
  const events = await getJson(page, `/api/v1/runtime-lab/sessions/${sessionId}/events`, `${caseId} events`)
  const trace = await getJson(page, `/api/v1/runtime-lab/sessions/${sessionId}/chatflow-trace`, `${caseId} trace`)
  assertNoMirrorEventPayloads(events, caseId)

  for (const expected of options.expectedTasks || []) {
    await expectTaskStatus(expected.sopId, expected.status)
  }
  if (options.expectedTasks?.length === 0) {
    assert(tasks.total === 0, `${caseId} expected no tasks, got ${JSON.stringify(tasks)}`)
  }
  if (options.requireResumeOffer) {
    await page.locator('.resume-box').waitFor({ timeout: 15_000 })
  }
  if (options.requireMultipleRuns) {
    const runIds = new Set(trace.tasks.map((task) => task.chatflow?.runId).filter(Boolean))
    assert(runIds.size >= 2, `${caseId} expected multiple child runs: ${JSON.stringify(trace)}`)
  }
  if (options.expectNoRuns) {
    assert(trace.total === 0, `${caseId} expected no child traces: ${JSON.stringify(trace)}`)
  }
  if (options.requireRun) {
    assert(trace.tasks.some((task) => task.chatflow?.runId > 0), `${caseId} expected at least one child run`)
  }
  if (options.requiredLedgerAction) {
    assert(
      events.list.some((event) => event.eventType === 'ROUTE_DECISION' && event.payload?.action === options.requiredLedgerAction),
      `${caseId} expected ledger action ${options.requiredLedgerAction}`,
    )
  }

  const eventStream = await eventStreamEvidence(page, trace, caseId)
  const recoveredTasks = await getJson(page, `/api/v1/runtime-lab/sessions/${sessionId}/tasks`, `${caseId} recovery tasks`)
  assert(recoveredTasks.total === tasks.total, `${caseId} task refresh changed total`)
  await page.getByTestId('chatflow-trace-panel').waitFor({ timeout: 15_000 })
  const screenshot = join(screenshotDir, `${caseId}.png`)
  await page.screenshot({ path: screenshot, fullPage: true })

  return {
    id: caseId,
    title: manifestCase.title,
    acceptance: manifestCase.acceptance,
    evidence: {
      apiResponse: {
        sessionId,
        taskTotal: tasks.total,
        eventTotal: events.total,
        traceTotal: trace.total,
        routeAction: await currentRouteAction(),
      },
      eventStream,
      taskPanel: {
        expectedTasks: options.expectedTasks || [],
        visible: true,
      },
      refreshRecovery: {
        taskTotal: recoveredTasks.total,
        screenshot,
      },
    },
    apiResponse: { tasks, events, trace },
  }
}

async function eventStreamEvidence(page, trace, caseId) {
  const task = trace.tasks.find((item) => item.chatflow?.eventStreamRef)
  if (!task) return { status: 'not_applicable', reason: 'no child run expected' }
  const frame = await getSseFrame(
    page,
    withParam(task.chatflow.eventStreamRef, '_testLimit', '1'),
    `${caseId} event stream`,
  )
  return {
    status: 'ok',
    runId: task.chatflow.runId,
    sequence: frame.sequence,
    type: frame.type,
    source: frame.source,
  }
}

function assertNoMirrorEventPayloads(events, caseId) {
  for (const event of events.list || []) {
    for (const key of Object.keys(event.payload || {})) {
      assert(!mirrorKeys.has(key), `${caseId} RuntimeLab event ${event.eventType} mirrors ${key}`)
    }
  }
}

async function getTraceTask(sessionId, sopId) {
  const trace = await getJson(page, `/api/v1/runtime-lab/sessions/${sessionId}/chatflow-trace`, `trace ${sopId}`)
  const task = trace.tasks.find((item) => item.sopId === sopId)
  assert(task, `expected trace for ${sopId}: ${JSON.stringify(trace)}`)
  return task
}

async function createFreshSession() {
  const previousSession = await page.locator('.session-id').innerText().catch(() => '')
  await page.getByRole('button', { name: '新会话' }).click()
  await page.waitForFunction(
    ({ previous }) => {
      const label = document.querySelector('.session-id')?.textContent || ''
      return /^#\d+$/.test(label.trim()) && label.trim() !== previous
    },
    { previous: previousSession.trim() },
    { timeout: 15_000 },
  )
  return currentSessionId()
}

async function currentSessionId() {
  const label = (await page.locator('.session-id').innerText()).trim()
  const match = label.match(/^#(\d+)$/)
  assert(match, `Expected numeric session label, got ${label}`)
  return Number(match[1])
}

async function currentRouteAction() {
  return (await page.getByTestId('route-action').innerText()).trim()
}

async function sendTurn(message) {
  await page.getByTestId('runtime-lab-input').fill(message)
  await page.getByTestId('runtime-lab-send').click()
}

async function waitForRouteAction(action) {
  await page.getByTestId('route-action').filter({ hasText: action }).waitFor({ timeout: 45_000 })
}

async function waitForAnyRouteAction(actions) {
  const pattern = new RegExp(actions.join('|'))
  await page.getByTestId('route-action').filter({ hasText: pattern }).waitFor({ timeout: 45_000 })
  const text = await currentRouteAction()
  const action = actions.find((item) => text.includes(item))
  assert(action, `Unexpected route action ${text}; expected ${actions.join(', ')}`)
  return action
}

async function waitForLedgerAction(sessionId, action) {
  const deadline = Date.now() + 45_000
  while (Date.now() < deadline) {
    const events = await getJson(page, `/api/v1/runtime-lab/sessions/${sessionId}/events`, `wait ${action}`)
    if (events.list.some((event) => event.eventType === 'ROUTE_DECISION' && event.payload?.action === action)) {
      return
    }
    await page.waitForTimeout(250)
  }
  throw new Error(`Timed out waiting for RuntimeLab ledger action ${action}`)
}

async function expectTaskStatus(sopId, status) {
  await page.locator('.task-row').filter({ hasText: sopId }).filter({ hasText: status }).last().waitFor({
    timeout: 45_000,
  })
}
