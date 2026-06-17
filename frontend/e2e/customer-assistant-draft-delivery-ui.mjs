import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright'

const __dirname = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(__dirname, '../..')
const artifactDir = process.env.HIFY_E2E_ARTIFACT_DIR
  || join(repoRoot, 'artifacts/slices/124-customer-assistant-draft-delivery-ui/124.1')
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

function eventTypes(result) {
  return result.list.map((event) => event.type)
}

function auditTypes(result) {
  return result.list.map((item) => item.eventType)
}

function serialize(value) {
  return JSON.stringify(value)
}

function assertRedacted(serialized, label) {
  for (const forbidden of ['13812345678', 'secret-token', 'raw-api-token']) {
    assert(!serialized.includes(forbidden), `${label} leaked ${forbidden}`)
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
  writeFileSync(
    notesPath,
    [
      '# UAT Notes',
      '',
      `Base URL: ${report.baseUrl}`,
      `Story: ${report.storyId}`,
      `Session: ${report.sessionId}`,
      `Action: ${report.actionId}`,
      `Status: ${report.status}`,
      `Delivery channel: ${report.deliveryChannel}`,
      '',
      '## Verified',
      '',
      '- Operator proposed-action panel renders the confirmed customer reply draft delivery control.',
      '- Customer lane does not expose the operator-only delivery control.',
      '- Confirming the draft changes status to CONFIRMED before delivery.',
      '- Clicking the delivery control changes status to SENT and renders the delivery receipt.',
      '- Event timeline and API events include draft_delivery_sent.',
      '- Operator audit includes draft_delivery_sent.',
      '- Page, proposed-action API payload, event payloads, and audit payloads redact raw phone/token values.',
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
  specId: '124-customer-assistant-draft-delivery-ui',
  baseUrl,
  storyId: 'refund_baggage_parallel',
  sessionId: null,
  actionId: Number(process.env.HIFY_DRAFT_DELIVERY_ACTION_ID || 0) || null,
  status: null,
  deliveryChannel: null,
  eventTypes: [],
  auditTypes: [],
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
  const story = stories.list.find((item) => item.storyId === report.storyId)
  assert(story, 'Expected seeded refund + baggage demo story')
  report.sessionId = story.sessionId

  await page.goto(`${baseUrl}/customer-assistant?view=demo&story=${encodeURIComponent(story.storyId)}`, {
    waitUntil: 'networkidle',
  })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText(`Session #${story.sessionId}`).first().waitFor({ state: 'visible', timeout: 10000 })

  const actionPanel = page.getByTestId('operator-proposed-actions-panel')
  await actionPanel.getByText('发送客户回复草稿').waitFor({ state: 'visible', timeout: 10000 })
  const customerLaneText = await page.getByTestId('customer-conversation-lane').innerText()
  assert(!customerLaneText.includes('外发草稿'), 'Customer lane must not render operator-only delivery control')

  let actionRow = actionPanel.locator('.action-row').filter({ hasText: '发送客户回复草稿' }).first()
  const pendingText = await actionRow.innerText()
  assert(pendingText.includes('PENDING'), `Expected draft action to start pending, got ${pendingText}`)
  assertRedacted(pendingText, 'pending action row')
  assert(
    await actionRow.locator('button').filter({ hasText: '外发草稿' }).isDisabled(),
    'Delivery button must stay disabled until the operator confirms the draft',
  )

  await actionRow.locator('button').filter({ hasText: '确认动作' }).click()
  await actionRow.getByText('CONFIRMED').waitFor({ state: 'visible', timeout: 10000 })
  actionRow = actionPanel.locator('.action-row').filter({ hasText: '发送客户回复草稿' }).first()
  assert(
    !(await actionRow.locator('button').filter({ hasText: '外发草稿' }).isDisabled()),
    'Delivery button should enable after confirmation',
  )

  await actionRow.locator('button').filter({ hasText: '外发草稿' }).click()
  await actionRow.getByText('SENT').waitFor({ state: 'visible', timeout: 10000 })
  await actionRow.getByTestId('operator-draft-delivery-receipt').waitFor({ state: 'visible', timeout: 10000 })
  await actionRow.getByText('投递回执').waitFor({ state: 'visible', timeout: 10000 })
  await actionRow.getByText('渠道 mock_web').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('operator-event-timeline').getByText('draft_delivery_sent').waitFor({
    state: 'visible',
    timeout: 10000,
  })

  const pageText = await page.locator('body').innerText()
  assertRedacted(pageText, 'customer assistant page')

  const actions = await api(page, `/customer-assistant/sessions/${story.sessionId}/proposed-actions`)
  const deliveredAction = actions.list.find((item) => item.title === '发送客户回复草稿')
  assert(deliveredAction, 'Expected delivered draft action from proposed-actions API')
  report.actionId = deliveredAction.id
  report.status = deliveredAction.status
  report.deliveryChannel = deliveredAction.result?.delivery?.channel
  assert(deliveredAction.status === 'SENT', `Expected SENT delivered action, got ${deliveredAction.status}`)
  assert(deliveredAction.result?.delivery?.messageId, 'Expected delivery message id in delivered action result')
  assertRedacted(serialize(deliveredAction), 'delivered action API')

  const events = await api(page, `/customer-assistant/sessions/${story.sessionId}/events`)
  const types = eventTypes(events)
  report.eventTypes = types
  assert(types.includes('proposed_action_confirmed'), 'Expected proposed_action_confirmed event')
  assert(types.includes('draft_delivery_started'), 'Expected draft_delivery_started event')
  assert(types.includes('draft_delivery_sent'), 'Expected draft_delivery_sent event')
  assertRedacted(serialize(events), 'event API')

  const audit = await api(page, `/customer-assistant/sessions/${story.sessionId}/operator-audit`)
  const auditEventTypes = auditTypes(audit)
  report.auditTypes = auditEventTypes
  assert(auditEventTypes.includes('draft_delivery_sent'), 'Expected draft_delivery_sent operator audit row')
  assertRedacted(serialize(audit), 'operator audit API')

  const pageMetrics = await page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    bodyLength: document.body.innerText.trim().length,
  }))
  assert(pageMetrics.overflowX <= 0, `Expected no horizontal overflow, got ${pageMetrics.overflowX}`)
  assert(pageMetrics.bodyLength > 0, 'Expected visible body text')
  report.pageMetrics = pageMetrics

  await saveScreenshot(page, report, 'draft-delivery-ui')
  assert(pageErrors.length === 0, `Unexpected browser page errors: ${pageErrors.join('; ')}`)
  writeReport(report)
  console.log('PASS customer assistant draft delivery UI browser uat')
} finally {
  await browser.close()
}
