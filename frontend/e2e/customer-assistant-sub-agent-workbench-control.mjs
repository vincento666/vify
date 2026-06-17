import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const __dirname = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(__dirname, '../..')
const artifactDir = process.env.HIFY_E2E_ARTIFACT_DIR
  || join(repoRoot, 'artifacts/slices/117-customer-assistant-sub-agent-workbench-controls/117.1')
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || join(artifactDir, 'screenshots')
const reportPath = process.env.HIFY_E2E_REPORT || join(artifactDir, 'uat-report.json')
const notesPath = process.env.HIFY_E2E_NOTES || join(artifactDir, 'uat.md')
const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const demoHostContext = resolveDemoHostContext()

function assert(condition, message) {
  if (!condition) throw new Error(message)
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

function hostHeaders() {
  return {
    'X-Hify-Actor-Id': demoHostContext.actorId,
    'X-Hify-Actor-Name': demoHostContext.actorName,
    'X-Hify-Tenant-Id': demoHostContext.tenantId,
    'X-Hify-Org-Id': demoHostContext.orgId,
    'X-Hify-Roles': demoHostContext.roles.join(','),
    'X-Hify-Permissions': demoHostContext.permissions.join(','),
    'X-Hify-Source': demoHostContext.source,
    'X-Hify-Locale': demoHostContext.locale,
  }
}

async function api(page, path, options = {}) {
  const method = options.method || 'GET'
  const response = await page.request.fetch(`${baseUrl}/api/v1${path}`, {
    method,
    data: options.data,
    headers: {
      'Content-Type': 'application/json',
      ...hostHeaders(),
      ...(options.headers || {}),
    },
  })
  assert(response.ok(), `${path} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${path} API ${payload.message}`)
  return payload.data
}

async function waitForControlText(page, text) {
  await page.waitForFunction(
    ({ expectedText }) => {
      const element = document.querySelector('[data-testid="operator-sub-agent-control"]')
      return Boolean(element?.textContent?.includes(expectedText))
    },
    { expectedText: text },
    { timeout: 20000 },
  )
}

function eventTypes(result) {
  return result.list.map((event) => event.type)
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
  writeFileSync(
    notesPath,
    [
      '# UAT Notes',
      '',
      `Base URL: ${report.baseUrl}`,
      `Story: ${report.storyId}`,
      `Session: ${report.sessionId}`,
      `Sub-agent run: ${report.subAgentRunId}`,
      `Status: ${report.status}`,
      '',
      '## Verified',
      '',
      '- Operator-only sub-agent control is visible in the progress checklist.',
      '- Clicking the control spawns the harness sub-agent and refreshes ledgers.',
      '- Browser timeline and API events include sub_agent_spawned, sub_agent_started, and sub_agent_completed.',
      '- Host context audit snapshot stayed scoped to the demo tenant.',
      '',
      '## Screenshots',
      '',
      report.screenshots.map((path) => `- ${path}`).join('\n'),
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
  specId: '117-customer-assistant-sub-agent-workbench-controls',
  baseUrl,
  hostContextTenant: demoHostContext.tenantId,
  storyId: null,
  sessionId: null,
  subAgentRunId: null,
  status: null,
  eventTypes: [],
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
  const story = stories.list.find((item) => item.storyId === 'refund_baggage_parallel') || stories.list[0]
  assert(story, 'Expected at least one seeded customer-assistant demo story')
  report.storyId = story.storyId
  report.sessionId = story.sessionId

  await page.goto(`${baseUrl}/customer-assistant?view=demo&story=${encodeURIComponent(story.storyId)}`, {
    waitUntil: 'networkidle',
  })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText(`Session #${story.sessionId}`).first().waitFor({ state: 'visible', timeout: 10000 })

  const control = page.getByTestId('operator-sub-agent-control')
  await control.getByText('后台子智能体').waitFor({ state: 'visible', timeout: 10000 })
  await control.getByText('未启动').waitFor({ state: 'visible', timeout: 10000 })
  const customerLaneText = await page.getByTestId('customer-conversation-lane').innerText()
  assert(!customerLaneText.includes('后台子智能体'), 'Customer lane must not render operator-only sub-agent control')

  const beforeEvents = await api(page, `/customer-assistant/sessions/${story.sessionId}/events`)
  await control.getByRole('button', { name: /启动子智能体/ }).click()
  await waitForControlText(page, '已完成')

  const controlText = await control.innerText()
  const publicRunMatch = controlText.match(/Run\s+(customer-assistant-run-(\d+))/)
  assert(publicRunMatch, `Expected visible sub-agent run id, got ${controlText}`)
  const runId = Number(publicRunMatch[2])
  report.subAgentRunId = publicRunMatch[1]

  await page
    .getByTestId('operator-event-timeline')
    .getByText('sub_agent_completed')
    .waitFor({ state: 'visible', timeout: 10000 })

  const run = await api(page, `/customer-assistant/runs/${runId}`)
  assert(run.status === 'completed', `Expected completed sub-agent run, got ${run.status}`)
  assert(run.subAgentRunId === report.subAgentRunId, 'Visible run id should match API run id')
  report.status = run.status

  const afterEvents = await api(page, `/customer-assistant/sessions/${story.sessionId}/events`)
  assert(afterEvents.total > beforeEvents.total, 'Expected sub-agent run to append session events')
  const types = eventTypes(afterEvents)
  report.eventTypes = types
  for (const type of ['sub_agent_spawned', 'sub_agent_started', 'sub_agent_progress', 'sub_agent_completed']) {
    assert(types.includes(type), `Expected event timeline to include ${type}`)
  }
  const snapshot = afterEvents.list.find((event) => event.type === 'session_context_snapshot')
  assert(snapshot, 'Expected host-context audit snapshot event after sub-agent run')
  assert(
    snapshot.payload?.hostContext?.tenantId === demoHostContext.tenantId,
    `Expected audit tenant ${demoHostContext.tenantId}`,
  )
  assert(
    String(snapshot.payload?.hostContext?.permissions || '').includes('customer_assistant:operate'),
    'Expected audit snapshot to include operate permission',
  )

  const tasks = await api(page, `/customer-assistant/sessions/${story.sessionId}/tasks`)
  const proposedActions = await api(page, `/customer-assistant/sessions/${story.sessionId}/proposed-actions`)
  const operatorAudit = await api(page, `/customer-assistant/sessions/${story.sessionId}/operator-audit`)
  assert(tasks.total >= 1, 'Expected refreshed task ledger after sub-agent run')
  assert(proposedActions.total >= 1, 'Expected refreshed proposed-action ledger after sub-agent run')
  assert(operatorAudit.total >= 1, 'Expected operator audit ledger to remain available after sub-agent run')

  const pageMetrics = await page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    bodyLength: document.body.innerText.trim().length,
  }))
  assert(pageMetrics.overflowX <= 0, `Expected no horizontal overflow, got ${pageMetrics.overflowX}`)
  assert(pageMetrics.bodyLength > 0, 'Expected visible body text')
  report.pageMetrics = pageMetrics

  await saveScreenshot(page, report, 'sub-agent-workbench-control')
  assert(pageErrors.length === 0, `Unexpected browser page errors: ${pageErrors.join('; ')}`)
  writeReport(report)
  console.log('PASS customer assistant sub-agent workbench control browser uat')
} finally {
  await browser.close()
}
