import { mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5175/runtime-lab/chat'
const artifactDir = resolve(process.cwd(), 'artifacts/slices/034-unified-routing-chat-lab/034.2')
const screenshotPath = resolve(artifactDir, 'browser-uat-unified-routing-chat-lab.png')
const reportPath = resolve(artifactDir, 'browser-uat.md')

mkdirSync(artifactDir, { recursive: true })

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const consoleMessages = []

page.on('console', (message) => {
  if (message.type() === 'error') consoleMessages.push(message.text())
})

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle' })
  await page.getByTestId('runtime-lab-chat').waitFor({ timeout: 15_000 })

  await page.getByTestId('open-sop-button').click()
  await waitForRouteAction(page, 'START_SOP')

  await page.locator('.sop-option').filter({ hasText: '发票申请' }).click()
  await page.getByTestId('open-sop-button').click()
  await waitForRouteAction(page, 'SUSPEND_AND_START')

  await sendTurn(page, '手机号 13800138000')
  await page.getByText('请回复 confirm 或 确认').waitFor({ timeout: 15_000 })

  await sendTurn(page, '确认')
  await waitForRouteAction(page, 'COMPLETE_TASK')
  await page.getByText('发票申请已完成。').waitFor({ timeout: 15_000 })

  await sendTurn(page, '继续')
  await waitForRouteAction(page, 'RESUME_TASK')
  await page.getByText('已恢复流程。请提供订单号。').waitFor({ timeout: 15_000 })
  await page.locator('.task-row').filter({ hasText: 'refund_ticket' }).filter({ hasText: 'RUNNING' }).waitFor({
    timeout: 15_000,
  })

  await page.screenshot({ path: screenshotPath, fullPage: true })

  const routeAction = await page.getByTestId('route-action').innerText()
  const report = [
    '# Browser UAT: Unified Routing Chat Lab',
    '',
    `- URL: ${baseUrl}`,
    '- Journey: refund_ticket -> invoice_apply -> complete invoice_apply -> resume refund_ticket',
    '- Expected actions: START_SOP, SUSPEND_AND_START, COMPLETE_TASK, RESUME_TASK',
    `- Final route action: ${routeAction}`,
    `- Screenshot: ${screenshotPath}`,
    `- Console errors: ${consoleMessages.length ? consoleMessages.join(' | ') : 'none'}`,
    '',
  ].join('\n')
  writeFileSync(reportPath, report)
  console.log(`Unified routing chat lab UAT passed: ${routeAction}`)
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
