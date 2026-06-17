import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

const stamp = Date.now()
const hostContext = {
  actorId: `operator-react-profile-${stamp}`,
  actorName: 'React Profile Operator',
  tenantId: `react-profile-tenant-${stamp}`,
  orgId: `react-profile-org-${stamp}`,
  source: 'mvp-demo-shell',
  roles: ['customer_service_operator'],
  permissions: ['customer_assistant:read', 'customer_assistant:operate'],
}
const hostHeaders = {
  'X-Hify-Actor-Id': hostContext.actorId,
  'X-Hify-Actor-Name': hostContext.actorName,
  'X-Hify-Tenant-Id': hostContext.tenantId,
  'X-Hify-Org-Id': hostContext.orgId,
  'X-Hify-Roles': hostContext.roles.join(','),
  'X-Hify-Source': hostContext.source,
  'X-Hify-Permissions': hostContext.permissions.join(','),
  'X-Request-Id': `req-140-react-profile-${stamp}`,
}
const profileId = 'refund_ticket_chatflow'
const defaultRefundProfile = {
  taskKey: 'refund_ticket',
  taskType: 'REFUND',
  workerType: 'chatflow_sop',
  workerRef: 'refund_ticket',
  modelPolicyRef: 'customer_assistant_chatflow_default',
  promptRef: 'refund_ticket_sop_prompt',
  toolRefs: ['refund_policy_lookup'],
  riskPolicyRef: 'manual_confirm',
  enabled: true,
}
const reactProfile = {
  taskKey: 'refund_ticket',
  taskType: 'REFUND',
  workerType: 'react_worker',
  workerRef: `configured_refund_react_${stamp}`,
  modelPolicyRef: `demo-react-model-${stamp}`,
  promptRef: `demo-react-prompt-${stamp}`,
  toolRefs: ['lookup_order'],
  riskPolicyRef: 'manual_confirm_high_risk',
  enabled: true,
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function api(page, path, options = {}) {
  return page.evaluate(
    async ({ path, options, hostHeaders }) => {
      const response = await fetch(`/api/v1${path}`, {
        headers: { 'Content-Type': 'application/json', ...hostHeaders, ...(options.headers || {}) },
        ...options,
      })
      return {
        ok: response.ok,
        status: response.status,
        body: await response.json(),
      }
    },
    { path, options, hostHeaders },
  )
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
let cleanupError = null

try {
  const hostParam = encodeURIComponent(JSON.stringify(hostContext))
  await page.goto(`${baseUrl}/customer-assistant?hifyHostContext=${hostParam}`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })

  const patched = await api(page, `/customer-assistant/worker-profiles/${profileId}`, {
    method: 'PATCH',
    body: JSON.stringify(reactProfile),
  })
  assert(patched.ok, `Expected react profile patch success, got ${patched.status}`)

  const created = await api(page, '/customer-assistant/sessions', {
    method: 'POST',
    body: JSON.stringify({ context: { source: 'react-worker-profile-config-uat' } }),
  })
  assert(created.ok, `Expected session create success, got ${created.status}`)
  const sessionId = created.body.data.id

  const turn = await api(page, `/customer-assistant/sessions/${sessionId}/turns`, {
    method: 'POST',
    body: JSON.stringify({ message: '我要退票', idempotencyKey: `react-profile-config-${stamp}` }),
  })
  assert(turn.ok, `Expected turn success, got ${turn.status}`)

  const tasks = await api(page, `/customer-assistant/sessions/${sessionId}/tasks`)
  assert(tasks.ok, `Expected task list success, got ${tasks.status}`)
  const task = tasks.body.data.list.find((item) => item.taskKey === 'refund_ticket')
  assert(task, 'Expected refund task after react profile turn')
  assert(task.workerType === 'react_worker', `Expected react_worker, got ${task.workerType}`)
  assert(task.workerRef === reactProfile.workerRef, `Expected worker ref ${reactProfile.workerRef}`)
  assert(task.status === 'COMPLETED', `Expected completed react task, got ${task.status}`)

  const configRefs = task.lastResult?.evidence?.workerConfigRefs
  assert(configRefs?.workerRef === reactProfile.workerRef, 'Expected react workerRef in evidence refs')
  assert(configRefs?.modelPolicyRef === reactProfile.modelPolicyRef, 'Expected model policy in evidence refs')
  assert(configRefs?.promptRef === reactProfile.promptRef, 'Expected prompt ref in evidence refs')
  assert(configRefs?.riskPolicyRef === reactProfile.riskPolicyRef, 'Expected risk policy in evidence refs')
  assert(
    JSON.stringify(configRefs?.toolRefs || []) === JSON.stringify(reactProfile.toolRefs),
    'Expected tool refs in evidence refs',
  )

  const events = await api(page, `/customer-assistant/sessions/${sessionId}/events`)
  assert(events.ok, `Expected event list success, got ${events.status}`)
  const completed = events.body.data.list.find((event) => event.type === 'react_worker_completed')
  assert(completed, 'Expected react_worker_completed event')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant react worker profile config browser uat')
} finally {
  if (!page.isClosed()) {
    try {
      const reset = await api(page, `/customer-assistant/worker-profiles/${profileId}`, {
        method: 'PATCH',
        body: JSON.stringify(defaultRefundProfile),
      })
      if (!reset.ok) cleanupError = new Error(`Failed to reset worker profile: ${reset.status}`)
    } catch (error) {
      cleanupError = error
    }
  }
  await browser.close()
  if (cleanupError) throw cleanupError
}
