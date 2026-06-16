import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

const hostContext = {
  actorId: 'mvp-demo-operator',
  actorName: 'MVP Demo Operator',
  tenantId: 'mvp-demo-tenant',
  orgId: 'mvp-demo-org',
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
  'X-Request-Id': 'req-097-worker-profile-uat',
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

const stamp = Date.now()
const configuredProfile = {
  taskKey: 'refund_ticket',
  taskType: 'QA',
  workerType: 'stub_qa',
  workerRef: `runtime_configured_refund_${stamp}`,
  modelPolicyRef: `demo-model-uat-${stamp}`,
  promptRef: `runtime-refund-prompt-${stamp}`,
  toolRefs: ['lookup_order', 'refund_policy_lookup'],
  riskPolicyRef: 'manual_confirm_high_risk',
  enabled: true,
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const hostParam = encodeURIComponent(JSON.stringify(hostContext))
  await page.goto(`${baseUrl}/customer-assistant?hifyHostContext=${hostParam}`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })

  const taskLedger = page.getByTestId('operator-task-ledger')
  const refundTaskRow = taskLedger.locator('.task-row').filter({ hasText: 'refund_ticket' }).first()
  await refundTaskRow.getByTestId('operator-task-profile').waitFor({ state: 'visible', timeout: 10000 })

  await refundTaskRow.getByRole('button', { name: '配置任务 Worker' }).click()
  await refundTaskRow.getByTestId('operator-worker-profile-edit-form').waitFor({ state: 'visible', timeout: 10000 })
  await refundTaskRow.getByLabel('任务类型').fill(configuredProfile.taskType)
  await refundTaskRow.getByLabel('Worker 类型').fill(configuredProfile.workerType)
  await refundTaskRow.getByLabel('Worker 引用').fill(configuredProfile.workerRef)
  await refundTaskRow.getByLabel('模型策略').fill(configuredProfile.modelPolicyRef)
  await refundTaskRow.getByLabel('提示词引用').fill(configuredProfile.promptRef)
  await refundTaskRow.getByLabel('风险策略').fill(configuredProfile.riskPolicyRef)
  await refundTaskRow.getByLabel('工具引用').fill(configuredProfile.toolRefs.join(', '))
  await refundTaskRow.getByRole('button', { name: /保存配置/ }).click()

  await refundTaskRow.getByText(configuredProfile.modelPolicyRef).waitFor({ state: 'visible', timeout: 10000 })
  await refundTaskRow.getByText(configuredProfile.riskPolicyRef).waitFor({ state: 'visible', timeout: 10000 })

  const profiles = await api(page, '/customer-assistant/worker-profiles')
  assert(profiles.ok, `Expected worker profile list success, got ${profiles.status}`)
  const updatedProfile = profiles.body.data.list.find((profile) => profile.profileId === profileId)
  assert(updatedProfile, 'Expected updated refund worker profile')
  assert(
    updatedProfile.modelPolicyRef === configuredProfile.modelPolicyRef,
    `Expected persisted model policy ${configuredProfile.modelPolicyRef}`,
  )

  const created = await api(page, '/customer-assistant/sessions', {
    method: 'POST',
    body: JSON.stringify({ context: { source: 'worker-profile-edit-e2e' } }),
  })
  assert(created.ok, `Expected session create success, got ${created.status}`)
  const sessionId = created.body.data.id

  const turn = await api(page, `/customer-assistant/sessions/${sessionId}/turns`, {
    method: 'POST',
    body: JSON.stringify({ message: '我要退票', idempotencyKey: `worker-profile-edit-${stamp}` }),
  })
  assert(turn.ok, `Expected turn success, got ${turn.status}`)

  const tasks = await api(page, `/customer-assistant/sessions/${sessionId}/tasks`)
  assert(tasks.ok, `Expected task list success, got ${tasks.status}`)
  const task = tasks.body.data.list.find((item) => item.taskKey === 'refund_ticket')
  assert(task, 'Expected refund task after configured profile turn')
  assert(task.workerType === configuredProfile.workerType, `Expected worker type ${configuredProfile.workerType}`)
  assert(task.workerRef === configuredProfile.workerRef, `Expected worker ref ${configuredProfile.workerRef}`)

  const events = await api(page, `/customer-assistant/sessions/${sessionId}/events`)
  assert(events.ok, `Expected event list success, got ${events.status}`)
  const recognized = events.body.data.list.find((event) => event.type === 'task_recognized')
  const profileRefs = recognized?.payload?.commands?.[0]?.profileRefs
  assert(profileRefs?.modelPolicyRef === configuredProfile.modelPolicyRef, 'Expected configured model refs in recognition event')
  assert(profileRefs?.riskPolicyRef === configuredProfile.riskPolicyRef, 'Expected configured risk refs in recognition event')

  await page.mouse.move(260, 260)
  await page.waitForTimeout(500)
  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant worker profile edit e2e')
} finally {
  if (!page.isClosed()) {
    await api(page, `/customer-assistant/worker-profiles/${profileId}`, {
      method: 'PATCH',
      body: JSON.stringify(defaultRefundProfile),
    }).catch(() => undefined)
  }
  await browser.close()
}
