import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function withHostContext(path, context) {
  return `${baseUrl}${path}?hifyHostContext=${encodeURIComponent(JSON.stringify(context))}`
}

const jobs = [
  {
    jobId: 901,
    runId: 701,
    ownerType: 'WORKFLOW',
    ownerId: 12,
    status: 'RUNNING',
    leaseOwner: 'worker-live',
    lastHeartbeatAt: '2026-07-04T01:02:03Z',
    leaseExpiresAt: '2026-07-04T01:03:03Z',
    attemptCount: 2,
    maxAttempts: 5,
    tenantId: 'tenant-job-live',
  },
  {
    jobId: 902,
    runId: 702,
    ownerType: 'CHATFLOW',
    ownerId: 13,
    status: 'QUEUED',
    attemptCount: 1,
    maxAttempts: 3,
    availableAt: '2026-07-04T01:05:00Z',
    nextRetryAt: '2026-07-04T01:05:00Z',
    lastError: 'provider timeout',
    tenantId: 'tenant-job-retry',
  },
]

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.route('**/api/v1/runtime-runs**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: 'OK', data: { list: [], total: 0, page: 1, pageSize: 20 } }),
    })
  })
  await page.route('**/api/v1/runtime-jobs**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: 'OK', data: { list: jobs, total: jobs.length, page: 1, pageSize: 20 } }),
    })
  })

  await page.goto(withHostContext('/runtime-ops', { permissions: ['runtime_ops:read'] }), { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: 'Jobs' }).click()
  const panel = page.getByTestId('runtime-ops-jobs')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  const text = await panel.textContent()

  assert(text.includes('worker-live'), 'Expected worker lease owner')
  assert(text.includes('2026-07-04T01:02:03Z'), 'Expected worker heartbeat timestamp')
  assert(text.includes('2 / 5'), 'Expected attempt count')
  assert(text.includes('2026-07-04T01:05:00Z'), 'Expected next retry timestamp')
  assert(text.includes('provider timeout'), 'Expected retry error evidence')

  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })

  console.log('PASS runtime ops job queue heartbeat and retry view')
} finally {
  await browser.close()
}
