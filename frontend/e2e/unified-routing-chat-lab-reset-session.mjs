import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5175/runtime-lab/chat'
const artifactSlice = process.env.HIFY_E2E_ARTIFACT_SLICE || '034.9'
const artifactDir = resolve(process.cwd(), `artifacts/slices/034-unified-routing-chat-lab/${artifactSlice}`)
const reportPath = resolve(artifactDir, 'browser-reset-session.md')

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
  const firstSession = (await page.locator('.session-id').innerText()).trim()

  await sendTurn(page, '我要退票')
  await waitForRouteAction(page, 'START_SOP')
  await page.locator('.lab-message').first().waitFor({ timeout: 15_000 })

  await page.getByTestId('runtime-lab-reset').click()
  await page.getByText('等待自由对话').waitFor({ timeout: 15_000 })
  await waitForRouteAction(page, '-')
  const resetSession = (await page.locator('.session-id').innerText()).trim()
  assert(/^#\d+$/.test(resetSession), `Expected reset session id, got ${resetSession}`)
  assert(resetSession !== firstSession, `Expected a new session id after reset, still ${resetSession}`)
  assert((await page.locator('.lab-message').count()) === 0, 'Expected transcript to be cleared')

  const report = [
    '# Browser UAT: Reset Runtime Lab Session',
    '',
    `- URL: ${baseUrl}`,
    `- First session: ${firstSession}`,
    `- Reset session: ${resetSession}`,
    '- Transcript cleared: yes',
    '- Route action reset: yes',
    `- Console errors: ${consoleMessages.length ? consoleMessages.join(' | ') : 'none'}`,
    `- Failed API responses: ${failedResponses.length ? failedResponses.join(' | ') : 'none'}`,
    '',
  ].join('\n')
  writeFileSync(reportPath, report)
  console.log('Unified routing chat lab reset session UAT passed')
} finally {
  await browser.close()
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
