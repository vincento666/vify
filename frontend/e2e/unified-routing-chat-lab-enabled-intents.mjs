import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5175/runtime-lab/chat'
const artifactSlice = process.env.HIFY_E2E_ARTIFACT_SLICE || '034.8'
const artifactDir = resolve(process.cwd(), `artifacts/slices/034-unified-routing-chat-lab/${artifactSlice}`)
const screenshotPath = resolve(artifactDir, 'browser-uat-enabled-intents.png')
const reportPath = resolve(artifactDir, 'browser-uat-enabled-intents.md')

const enabledSopIds = ['flight_booking', 'invoice_apply']
const disabledSopIds = [
  'fare_quote',
  'group_booking',
  'ancillary_sales',
  'refund_ticket',
  'change_flight',
  'passenger_info_change',
  'baggage_service',
  'seat_checkin',
  'flight_status',
  'special_assistance',
  'pet_cabin',
  'irregular_flight',
  'membership_service',
]

mkdirSync(artifactDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const sentScopes = []
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
page.on('request', (request) => {
  if (!request.url().includes('/api/v1/runtime-lab/sessions/') || !request.url().endsWith('/messages')) return
  const payload = request.postDataJSON()
  if (payload && Array.isArray(payload.enabledSopIds)) sentScopes.push(payload.enabledSopIds)
})

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  await page.getByTestId('runtime-lab-chat').waitFor({ timeout: 15_000 })
  await page.locator('.sop-option').last().waitFor({ timeout: 15_000 })

  for (const sopId of enabledSopIds) {
    await expectChecked(page, sopId, true)
  }
  for (const sopId of disabledSopIds) {
    await page.getByTestId(`sop-toggle-${sopId}`).click()
    await expectChecked(page, sopId, false)
  }

  await sendTurn(page, '我要退票')
  await waitForRouteAction(page, 'NO_MATCH')
  assert((await page.locator('.task-row').filter({ hasText: 'refund_ticket' }).count()) === 0, 'refund_ticket was started')

  await sendTurn(page, '我想买一张明天去上海的机票')
  await waitForRouteAction(page, 'START_SOP')
  await expectTaskStatus(page, 'flight_booking', 'RUNNING')

  await sendTurn(page, '公司报销要凭证，帮我开一下电子发票')
  await waitForRouteAction(page, 'SUSPEND_AND_START')
  await expectTaskStatus(page, 'invoice_apply', 'RUNNING')

  assert(sentScopes.length >= 3, `Expected at least 3 scoped message requests, got ${sentScopes.length}`)
  for (const scope of sentScopes.slice(-3)) {
    assert(JSON.stringify(scope) === JSON.stringify(enabledSopIds), `Unexpected enabled scope: ${scope.join(',')}`)
  }

  await page.screenshot({ path: screenshotPath, fullPage: true })
  const report = [
    '# Browser UAT: Enabled Intent Scope',
    '',
    `- URL: ${baseUrl}`,
    `- Enabled SOP ids: ${enabledSopIds.join(', ')}`,
    '- Disabled refund utterance: NO_MATCH',
    '- Enabled booking utterance: START_SOP flight_booking',
    '- Enabled invoice utterance: SUSPEND_AND_START invoice_apply',
    `- Scoped message requests observed: ${sentScopes.length}`,
    `- Screenshot: ${screenshotPath}`,
    `- Console errors: ${consoleMessages.length ? consoleMessages.join(' | ') : 'none'}`,
    `- Failed API responses: ${failedResponses.length ? failedResponses.join(' | ') : 'none'}`,
    '',
  ].join('\n')
  writeFileSync(reportPath, report)
  console.log('Unified routing chat lab enabled intent scope UAT passed')
} finally {
  await browser.close()
}

async function expectChecked(page, sopId, expected) {
  const checked = await page.getByTestId(`sop-toggle-${sopId}`).isChecked()
  assert(checked === expected, `Expected ${sopId} checked=${expected}, got ${checked}`)
}

async function expectTaskStatus(page, sopId, status) {
  await page.locator('.task-row').filter({ hasText: sopId }).filter({ hasText: status }).last().waitFor({
    timeout: 15_000,
  })
}

async function sendTurn(page, message) {
  await page.getByTestId('runtime-lab-input').fill(message)
  await page.getByTestId('runtime-lab-send').click()
}

async function waitForRouteAction(page, action) {
  await page.getByTestId('route-action').filter({ hasText: action }).waitFor({ timeout: 15_000 })
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}
