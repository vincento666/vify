import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const screenshotBeforePath = process.env.HIFY_E2E_SCREENSHOT_BEFORE

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function withHostContext(path, context) {
  return `${baseUrl}${path}?hifyHostContext=${encodeURIComponent(JSON.stringify(context))}`
}

let jobs = [
  {
    jobId: 910,
    runId: 810,
    ownerType: 'WORKFLOW',
    ownerId: 15,
    status: 'FAILED',
    attemptCount: 3,
    maxAttempts: 3,
    lastError: 'provider timeout',
    tenantId: 'tenant-dlq-retry',
    updatedAt: '2026-07-04T02:00:00Z',
  },
  {
    jobId: 911,
    runId: 811,
    ownerType: 'CHATFLOW',
    ownerId: 16,
    status: 'FAILED',
    attemptCount: 3,
    maxAttempts: 3,
    lastError: 'tool failed',
    tenantId: 'tenant-dlq-ignore',
    updatedAt: '2026-07-04T02:01:00Z',
  },
  {
    jobId: 912,
    runId: 812,
    ownerType: 'WORKFLOW',
    ownerId: 17,
    status: 'FAILED',
    attemptCount: 2,
    maxAttempts: 2,
    lastError: 'manual fix applied',
    tenantId: 'tenant-dlq-resolve',
    updatedAt: '2026-07-04T02:02:00Z',
  },
]
const actionCalls = []
const confirms = []

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  page.on('dialog', async (dialog) => {
    confirms.push(dialog.message())
    await dialog.accept()
  })
  await page.route('**/api/v1/runtime-runs**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: 'OK', data: { list: [], total: 0, page: 1, pageSize: 20 } }),
    })
  })
  await page.route('**/api/v1/runtime-jobs/dlq**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: 'OK', data: { list: jobs, total: jobs.length, page: 1, pageSize: 20 } }),
    })
  })
  await page.route(/\/api\/v1\/runtime-jobs\/(\d+)\/(retry|ignore|mark-resolved)$/, async (route) => {
    const match = route.request().url().match(/runtime-jobs\/(\d+)\/(retry|ignore|mark-resolved)$/)
    const jobId = Number(match?.[1])
    const action = String(match?.[2])
    actionCalls.push(`${jobId}:${action}`)
    jobs = jobs.filter((job) => job.jobId !== jobId)
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: 'OK', data: { jobId, status: action === 'retry' ? 'QUEUED' : action === 'ignore' ? 'IGNORED' : 'RESOLVED' } }),
    })
  })

  await page.goto(withHostContext('/runtime-ops', { permissions: ['runtime_ops:read'] }), { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: 'DLQ' }).click()
  const panel = page.getByTestId('runtime-ops-dlq')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText('provider timeout').waitFor({ state: 'visible', timeout: 10000 })
  if (screenshotBeforePath) await page.screenshot({ path: screenshotBeforePath, fullPage: true })

  await page.getByTestId('runtime-ops-dlq-retry-910').click()
  await page.getByTestId('runtime-ops-dlq-ignore-911').click()
  await page.getByTestId('runtime-ops-dlq-resolve-912').click()
  await page.waitForFunction(() => document.querySelectorAll('[data-testid="runtime-ops-dlq-row"]').length === 0)

  const text = await panel.textContent()
  assert(text.includes('Total 0'), `Expected empty DLQ after actions, got: ${text}`)
  assert(actionCalls.includes('910:retry'), 'Expected retry action call')
  assert(actionCalls.includes('911:ignore'), 'Expected ignore action call')
  assert(actionCalls.includes('912:mark-resolved'), 'Expected mark-resolved action call')
  assert(confirms.length === 3, `Expected 3 DLQ confirmation dialogs, got ${confirms.length}`)

  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })

  console.log('PASS runtime ops DLQ retry ignore mark-resolved actions')
} finally {
  await browser.close()
}
