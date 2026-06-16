import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173/runtime-lab/chat'
const artifactSlice = process.env.HIFY_E2E_ARTIFACT_SLICE || '105.1'
const artifactDir = resolve(process.cwd(), `artifacts/slices/105-runtime-lab-sop-chatflow-v2-binding/${artifactSlice}`)
const screenshotPath =
  process.env.HIFY_E2E_SCREENSHOT || resolve(artifactDir, 'screenshots/runtime-lab-sop-v2-binding.png')
const reportPath = resolve(artifactDir, 'browser-uat.md')

mkdirSync(resolve(artifactDir, 'screenshots'), { recursive: true })

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const consoleMessages = []
const failedResponses = []

page.on('console', (message) => {
  if (message.type() === 'error') consoleMessages.push(message.text())
})
page.on('response', (response) => {
  if (response.url().includes('/api/') && response.status() >= 400) {
    failedResponses.push(`${response.status()} ${response.url()}`)
  }
})

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  await page.getByTestId('runtime-lab-chat').waitFor({ timeout: 15_000 })
  await createFreshSession(page)

  const sessionId = await currentSessionId(page)

  await selectSop(page, '退票办理')
  await sendTurn(page, '我要退票')
  await waitForRouteAction(page, 'START_SOP')
  await expectTaskStatus(page, 'refund_ticket', 'RUNNING')
  await expectTraceNode(page, 'info_order')

  await selectSop(page, '发票申请')
  await sendTurn(page, '我要开发票')
  await waitForRouteAction(page, 'SUSPEND_AND_START')
  await expectTaskStatus(page, 'refund_ticket', 'SUSPENDED')
  await expectTaskStatus(page, 'invoice_apply', 'RUNNING')

  await sendTurn(page, '确认')
  await waitForRouteAction(page, 'COMPLETE_TASK')
  await expectTaskStatus(page, 'invoice_apply', 'COMPLETED')

  await sendTurn(page, '继续处理退票')
  await waitForRouteAction(page, 'RESUME_TASK')
  await expectTaskStatus(page, 'refund_ticket', 'RUNNING')
  await expectTraceNode(page, 'info_order')

  await sendTurn(page, '手机号 13800138000')
  await waitForRouteAction(page, 'CONTINUE_ACTIVE_SOP')
  await expectTraceNode(page, 'confirm_1')

  await sendTurn(page, '确认')
  await waitForRouteAction(page, 'COMPLETE_TASK')
  await expectTaskStatus(page, 'refund_ticket', 'COMPLETED')

  const trace = await fetchTrace(page, sessionId)
  const refundTrace = trace.tasks.find((task) => task.sopId === 'refund_ticket')
  assert(refundTrace, 'Expected refund_ticket trace task')
  const eventTypes = refundTrace.events.map((event) => event.type)
  assert(eventTypes.includes('workflow_run_started'), `Missing v2 start event: ${eventTypes.join(',')}`)
  assert(eventTypes.includes('workflow_run_resumed'), `Missing v2 resume event: ${eventTypes.join(',')}`)
  assert(eventTypes.includes('workflow_node_waiting'), `Missing v2 waiting event: ${eventTypes.join(',')}`)

  assert(failedResponses.length === 0, `Failed API responses: ${failedResponses.join(' | ')}`)
  await page.screenshot({ path: screenshotPath, fullPage: true })

  const report = [
    '# Browser UAT: Runtime Lab SOP Chatflow V2 Binding',
    '',
    `- URL: ${baseUrl}`,
    `- Session: #${sessionId}`,
    '- Journey: refund_ticket starts through Chatflow runtime v2, invoice_apply interrupts as a second bound SOP, refund_ticket resumes through runtime v2',
    `- Observed refund trace events: ${eventTypes.join(', ')}`,
    `- Screenshot: ${screenshotPath}`,
    `- Console errors: ${consoleMessages.length ? consoleMessages.join(' | ') : 'none'}`,
    `- Failed API responses: ${failedResponses.length ? failedResponses.join(' | ') : 'none'}`,
    '',
  ].join('\n')
  writeFileSync(reportPath, report)
  console.log('Runtime Lab SOP Chatflow v2 binding UAT passed')
} finally {
  await browser.close()
}

async function createFreshSession(page) {
  const sessionLabel = page.locator('.session-id')
  const previousSession = await sessionLabel.innerText().catch(() => '')
  await page.getByRole('button', { name: '新会话' }).click()
  await page.waitForFunction(
    ({ previous }) => {
      const label = document.querySelector('.session-id')?.textContent || ''
      return /^#\d+$/.test(label.trim()) && label.trim() !== previous
    },
    { previous: previousSession.trim() },
    { timeout: 15_000 },
  )
}

async function currentSessionId(page) {
  const label = (await page.locator('.session-id').innerText()).trim()
  const match = label.match(/^#(\d+)$/)
  assert(match, `Expected numeric session label, got ${label}`)
  return Number(match[1])
}

async function selectSop(page, label) {
  await page.locator('.enabled-scope-chip').filter({ hasText: label }).waitFor({ timeout: 15_000 })
}

async function expectTaskStatus(page, sopId, status) {
  await page.locator('.task-row').filter({ hasText: sopId }).filter({ hasText: status }).last().waitFor({
    timeout: 45_000,
  })
}

async function expectTraceNode(page, nodeKey) {
  await page.getByTestId('runtime-lab-trace-node').filter({ hasText: nodeKey }).last().waitFor({
    timeout: 45_000,
  })
}

async function sendTurn(page, message) {
  await page.getByTestId('runtime-lab-input').fill(message)
  await page.getByTestId('runtime-lab-send').click()
}

async function waitForRouteAction(page, action) {
  await page.getByTestId('route-action').filter({ hasText: action }).waitFor({ timeout: 45_000 })
}

async function fetchTrace(page, sessionId) {
  const traceUrl = new URL(`/api/v1/runtime-lab/sessions/${sessionId}/chatflow-trace`, baseUrl).toString()
  const response = await page.request.get(traceUrl)
  assert(response.ok(), `Trace request failed: ${response.status()} ${await response.text()}`)
  const payload = await response.json()
  return payload.data
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}
