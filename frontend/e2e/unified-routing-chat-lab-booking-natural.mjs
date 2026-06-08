import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5175/runtime-lab/chat'
const artifactSlice = process.env.HIFY_E2E_ARTIFACT_SLICE || '034.9'
const artifactDir = resolve(process.cwd(), `artifacts/slices/034-unified-routing-chat-lab/${artifactSlice}`)
const reportPath = resolve(artifactDir, 'browser-booking-natural.md')

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

  await sendTurn(page, '我要定航班')
  await waitForRouteAction(page, 'START_SOP')
  let assistantText = await page.locator('.lab-message.assistant .message-content').last().innerText()
  assert(!assistantText.includes('订单号'), assistantText)
  assert(assistantText.includes('手机号'), assistantText)
  assert(assistantText.includes('乘机人'), assistantText)

  await page.getByTestId('runtime-lab-reset').click()
  await page.getByText('等待自由对话').waitFor({ timeout: 15_000 })

  await sendTurn(page, '我要订一张明天上午9点从北京到广州的机票')
  await waitForRouteAction(page, 'START_SOP')
  assistantText = await page.locator('.lab-message.assistant .message-content').last().innerText()
  assert(!assistantText.includes('订单号'), assistantText)
  assert(assistantText.includes('北京'), assistantText)
  assert(assistantText.includes('广州'), assistantText)
  assert(assistantText.includes('手机号'), assistantText)
  assert(assistantText.includes('乘机人'), assistantText)

  const report = [
    '# Browser UAT: Natural Booking Turns',
    '',
    `- URL: ${baseUrl}`,
    '- Short utterance: 我要定航班 -> START_SOP flight_booking',
    '- Detailed utterance: 我要订一张明天上午9点从北京到广州的机票 -> START_SOP flight_booking',
    '- Booking prompt mentions order number: no',
    `- Console errors: ${consoleMessages.length ? consoleMessages.join(' | ') : 'none'}`,
    `- Failed API responses: ${failedResponses.length ? failedResponses.join(' | ') : 'none'}`,
    '',
  ].join('\n')
  writeFileSync(reportPath, report)
  console.log('Unified routing chat lab natural booking UAT passed')
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
