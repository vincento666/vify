import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const screenshotRunsPath = process.env.HIFY_E2E_SCREENSHOT_RUNS
const screenshotJobsPath = process.env.HIFY_E2E_SCREENSHOT_JOBS

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function withHostContext(path, context) {
  return `${baseUrl}${path}?hifyHostContext=${encodeURIComponent(JSON.stringify(context))}`
}

const runs = [
  {
    runId: 701,
    ownerType: 'WORKFLOW',
    ownerId: 12,
    ownerName: 'Safe Cancel Run',
    status: 'RUNNING',
    state: 'running',
    tenantId: 'tenant-safe',
    queueState: 'running',
    createdAt: '2026-07-04T03:00:00Z',
    updatedAt: '2026-07-04T03:01:00Z',
  },
  {
    runId: 702,
    ownerType: 'CHATFLOW',
    ownerId: 13,
    ownerName: 'Safe Resume Run',
    status: 'INTERRUPTED',
    state: 'waiting',
    tenantId: 'tenant-safe',
    queueState: 'completed',
    createdAt: '2026-07-04T03:02:00Z',
    updatedAt: '2026-07-04T03:03:00Z',
  },
]

const jobs = [
  {
    jobId: 910,
    runId: 810,
    ownerType: 'WORKFLOW',
    ownerId: 15,
    status: 'FAILED',
    attemptCount: 3,
    maxAttempts: 3,
    lastError: 'provider timeout',
    tenantId: 'tenant-safe',
    updatedAt: '2026-07-04T03:04:00Z',
  },
  {
    jobId: 912,
    runId: 812,
    ownerType: 'WORKFLOW',
    ownerId: 17,
    status: 'RESOLVED',
    attemptCount: 2,
    maxAttempts: 2,
    lastError: 'operator fixed',
    tenantId: 'tenant-safe',
    updatedAt: '2026-07-04T03:05:00Z',
  },
]

const calls = []
const confirms = []
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  page.on('dialog', async (dialog) => {
    confirms.push(dialog.message())
    await dialog.accept()
  })
  await page.route(/\/api\/v1\/runtime-runs(?:\?.*)?$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: 'OK', data: { list: runs, total: runs.length, page: 1, pageSize: 20 } }),
    })
  })
  await page.route('**/api/v1/runtime-runs/701/cancel', async (route) => {
    calls.push('cancel-run')
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: { runId: 701, status: 'CANCELLED' } }) })
  })
  await page.route('**/api/v1/runtime-runs/702/resume', async (route) => {
    calls.push('resume-run')
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: { runId: 702, status: 'SUCCEEDED' } }) })
  })
  await page.route('**/api/v1/runtime-jobs**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: 'OK', data: { list: jobs, total: jobs.length, page: 1, pageSize: 20 } }),
    })
  })
  await page.route('**/api/v1/runtime-jobs/910/retry', async (route) => {
    calls.push('retry-job')
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: { jobId: 910, status: 'QUEUED' } }) })
  })
  await page.route('**/api/v1/runtime-jobs/912/reopen', async (route) => {
    calls.push('reopen-dlq')
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ code: 200, message: 'OK', data: { jobId: 912, status: 'FAILED' } }) })
  })

  await page.goto(withHostContext('/runtime-ops', { permissions: ['runtime_ops:read'] }), { waitUntil: 'networkidle' })
  await page.getByText('Safe Cancel Run').waitFor({ state: 'visible', timeout: 10000 })
  if (screenshotRunsPath) await page.screenshot({ path: screenshotRunsPath, fullPage: true })
  await page.getByTestId('runtime-ops-safe-cancel-run-701').click()
  await page.getByTestId('runtime-ops-safe-resume-run-702').click()
  await page.getByRole('tab', { name: 'Jobs' }).click()
  await page.getByText('provider timeout').waitFor({ state: 'visible', timeout: 10000 })
  if (screenshotJobsPath) await page.screenshot({ path: screenshotJobsPath, fullPage: true })
  await page.getByTestId('runtime-ops-safe-retry-job-910').click()
  await page.getByTestId('runtime-ops-safe-reopen-dlq-912').click()

  assert(confirms.length === 4, `Expected 4 confirmation dialogs, got ${confirms.length}`)
  for (const expected of ['cancel-run', 'resume-run', 'retry-job', 'reopen-dlq']) {
    assert(calls.includes(expected), `Expected ${expected} API call`)
  }

  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })

  console.log('PASS runtime ops safe actions confirm and audit calls')
} finally {
  await browser.close()
}
