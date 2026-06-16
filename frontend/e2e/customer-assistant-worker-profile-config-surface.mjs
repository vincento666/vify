import { mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
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

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const workerProfilesResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'GET' && response.url().includes('/api/v1/customer-assistant/worker-profiles'),
    { timeout: 10000 },
  )
  const hostParam = encodeURIComponent(JSON.stringify(hostContext))

  await page.goto(`${baseUrl}/customer-assistant?hifyHostContext=${hostParam}`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })

  const response = await workerProfilesResponse
  assert(response.ok(), `Expected worker profile backend response, got ${response.status()}`)
  const payload = await response.json()
  const profiles = payload?.data?.list ?? []
  assert(profiles.length > 0, 'Expected at least one backend worker profile')

  const profilePanel = page.getByTestId('operator-worker-profile-config-panel')
  await profilePanel.waitFor({ state: 'visible', timeout: 10000 })
  await profilePanel.getByText('Worker 配置').waitFor({ state: 'visible', timeout: 10000 })

  const firstProfile = profiles[0]
  const firstProfileRow = profilePanel.getByTestId('operator-worker-profile-row').filter({
    hasText: firstProfile.profileId,
  })
  await firstProfileRow.waitFor({ state: 'visible', timeout: 10000 })
  await firstProfileRow.getByText(`${firstProfile.taskType} · ${firstProfile.taskKey}`).waitFor({
    state: 'visible',
    timeout: 10000,
  })
  await firstProfileRow.getByText(`${firstProfile.workerType} · ${firstProfile.workerRef}`).waitFor({
    state: 'visible',
    timeout: 10000,
  })
  await firstProfileRow.getByText(`模型 ${firstProfile.modelPolicyRef}`).waitFor({ state: 'visible', timeout: 10000 })
  await firstProfileRow.getByText(`提示词 ${firstProfile.promptRef}`).waitFor({ state: 'visible', timeout: 10000 })
  await firstProfileRow.getByText(`风险 ${firstProfile.riskPolicyRef}`).waitFor({ state: 'visible', timeout: 10000 })

  const requestHeaders = response.request().headers()
  assert(requestHeaders['x-hify-tenant-id'] === hostContext.tenantId, 'Expected demo tenant header on profile request')
  assert(requestHeaders['x-hify-actor-id'] === hostContext.actorId, 'Expected demo actor header on profile request')

  await firstProfileRow.getByRole('button', { name: '配置 Worker Profile' }).click()
  await firstProfileRow.getByTestId('operator-worker-profile-catalog-edit-form').waitFor({
    state: 'visible',
    timeout: 10000,
  })
  await firstProfileRow.getByRole('button', { name: /取消配置/ }).click()

  if (screenshotPath) {
    mkdirSync(dirname(screenshotPath), { recursive: true })
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant worker profile config surface e2e')
} finally {
  await browser.close()
}
