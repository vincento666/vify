import { mkdir } from 'node:fs/promises'
import { join } from 'node:path'

import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function withHostContext(path, context) {
  return `${baseUrl}${path}?hifyHostContext=${encodeURIComponent(JSON.stringify(context))}`
}

const ownerTypes = ['WORKFLOW', 'CHATFLOW', 'CUSTOMER_ASSISTANT', 'SOP']
const states = ['queued', 'running', 'waiting', 'succeeded', 'failed', 'cancelled']
const stateStatus = {
  queued: 'RUNNING',
  running: 'RUNNING',
  waiting: 'INTERRUPTED',
  succeeded: 'SUCCEEDED',
  failed: 'FAILED',
  cancelled: 'CANCELLED',
}
const runs = ownerTypes.flatMap((ownerType, ownerIndex) =>
  states.map((state, stateIndex) => ({
    runId: 700 + ownerIndex * 10 + stateIndex,
    ownerType,
    ownerId: 100 + ownerIndex,
    ownerName: `${ownerType} ${state}`,
    status: stateStatus[state],
    state,
    tenantId: `${ownerType.toLowerCase()}-${state}`,
    queueState: state === 'queued' ? 'queued' : state === 'running' ? 'running' : 'completed',
    createdAt: `2026-07-04T0${ownerIndex}:0${stateIndex}:00Z`,
    updatedAt: `2026-07-04T0${ownerIndex}:1${stateIndex}:00Z`,
  })),
)

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  if (screenshotDir) await mkdir(screenshotDir, { recursive: true })
  await page.route('**/api/v1/runtime-runs**', async (route) => {
    const url = new URL(route.request().url())
    const ownerType = url.searchParams.get('ownerType')
    const state = url.searchParams.get('state')
    const tenantId = url.searchParams.get('tenantId')
    const filtered = runs.filter((run) => {
      if (ownerType && run.ownerType !== ownerType) return false
      if (state && run.state !== state) return false
      if (tenantId && run.tenantId !== tenantId) return false
      return true
    })
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: 'OK', data: { list: filtered, total: filtered.length, page: 1, pageSize: 20 } }),
    })
  })

  await page.goto(withHostContext('/runtime-ops', { permissions: ['runtime_ops:read'] }), { waitUntil: 'networkidle' })
  await page.getByTestId('runtime-ops-run-list').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText('WORKFLOW running').waitFor({ state: 'visible', timeout: 10000 })

  for (const ownerType of ownerTypes) {
    for (const state of states) {
      const tenantId = `${ownerType.toLowerCase()}-${state}`
      const ownerName = `${ownerType} ${state}`
      await page.getByTestId('runtime-ops-owner-filter').selectOption(ownerType)
      await page.getByTestId('runtime-ops-state-filter').selectOption(state)
      await page.getByTestId('runtime-ops-tenant-filter').fill(tenantId)
      await page.getByTestId('runtime-ops-apply-filters').click()
      await page.waitForFunction(
        () => document.querySelectorAll('[data-testid="runtime-ops-run-row"]').length === 1,
        undefined,
        { timeout: 10000 },
      )
      await page.getByText(ownerName).waitFor({ state: 'visible', timeout: 10000 })
      await page.getByText(tenantId).waitFor({ state: 'visible', timeout: 10000 })
      if (screenshotDir) {
        await page.screenshot({ path: join(screenshotDir, `${ownerType.toLowerCase()}-${state}.png`), fullPage: true })
      }
    }
  }

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS runtime ops run list filters combos=${ownerTypes.length * states.length}`)
} finally {
  await browser.close()
}
