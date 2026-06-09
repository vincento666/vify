import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5175/runtime-lab/chat'
const artifactSlice = process.env.HIFY_E2E_ARTIFACT_SLICE || '034.7'
const artifactDir = resolve(process.cwd(), `artifacts/slices/034-unified-routing-chat-lab/${artifactSlice}`)
const hiddenScreenshotPath = resolve(artifactDir, 'browser-uat-intent-samples-hidden.png')
const screenshotPath = resolve(artifactDir, 'browser-uat-intent-samples-toggle.png')
const reportPath = resolve(artifactDir, 'browser-uat.md')

mkdirSync(artifactDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1366, height: 820 } })
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

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  await page.getByTestId('runtime-lab-chat').waitFor({ timeout: 15_000 })
  await page.locator('.enabled-scope-chip').last().waitFor({ timeout: 15_000 })
  const initialCount = await page.locator('.enabled-scope-chip').count()
  assert(initialCount === 15, `Expected 15 SOP samples before hiding, got ${initialCount}`)

  const toggle = page.getByTestId('intent-samples-toggle')
  await toggle.waitFor({ timeout: 15_000 })
  await toggle.click()
  await page.locator('.enabled-scope-chip').first().waitFor({ state: 'detached', timeout: 15_000 })
  assert((await page.locator('.sample-chip').count()) === 0, 'Expected trigger/reply samples to be hidden')

  await sendTurn(page, '您好，我想退票，确认一下票款规则')
  await page.getByTestId('route-action').filter({ hasText: 'START_SOP' }).waitFor({ timeout: 15_000 })
  await page.locator('.task-row').filter({ hasText: 'refund_ticket' }).filter({ hasText: 'RUNNING' }).waitFor({
    timeout: 15_000,
  })
  await page.screenshot({ path: hiddenScreenshotPath, fullPage: true })

  await toggle.click()
  await page.locator('.enabled-scope-chip').last().waitFor({ timeout: 15_000 })
  const restoredCount = await page.locator('.enabled-scope-chip').count()
  assert(restoredCount === 15, `Expected 15 SOP samples after showing, got ${restoredCount}`)

  await page.screenshot({ path: screenshotPath, fullPage: true })
  const report = [
    '# Browser UAT: Intent Samples Toggle',
    '',
    `- URL: ${baseUrl}`,
    `- Initial SOP samples: ${initialCount}`,
    '- Hidden state: SOP samples and sample chips removed',
    '- Free chat while hidden: refund_ticket START_SOP passed',
    `- Restored SOP samples: ${restoredCount}`,
    `- Hidden screenshot: ${hiddenScreenshotPath}`,
    `- Restored screenshot: ${screenshotPath}`,
    `- Console errors: ${consoleMessages.length ? consoleMessages.join(' | ') : 'none'}`,
    `- Failed API responses: ${failedResponses.length ? failedResponses.join(' | ') : 'none'}`,
    '',
  ].join('\n')
  writeFileSync(reportPath, report)
  console.log('Unified routing chat lab intent samples toggle UAT passed')
} finally {
  await browser.close()
}

async function sendTurn(page, message) {
  await page.getByTestId('runtime-lab-input').fill(message)
  await page.getByTestId('runtime-lab-send').click()
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}
