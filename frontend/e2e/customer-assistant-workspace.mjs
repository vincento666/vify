import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })

  for (const testId of [
    'customer-conversation-lane',
    'operator-conversation-lane',
    'operator-task-ledger',
    'operator-recommendation-panel',
    'operator-draft-panel',
    'operator-proposed-actions-panel',
    'operator-event-timeline',
    'operator-warnings-panel',
  ]) {
    assert(await page.getByTestId(testId).isVisible(), `Expected ${testId} to be visible`)
  }

  const customerText = await page.getByTestId('customer-conversation-lane').innerText()
  assert(customerText.includes('客户侧'), 'Expected customer lane title')
  assert(!customerText.includes('确认动作'), 'Customer lane must not expose internal action controls')
  assert(!customerText.includes('任务台账'), 'Customer lane must not expose task ledger')

  const pageMetrics = await page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    hasDraft: document.body.textContent.includes('客户回复草稿'),
    hasRecommendation: document.body.textContent.includes('坐席建议'),
  }))

  assert(pageMetrics.overflowX <= 0, `Expected no horizontal overflow, got ${pageMetrics.overflowX}`)
  assert(pageMetrics.hasDraft, 'Expected customer reply draft panel')
  assert(pageMetrics.hasRecommendation, 'Expected operator recommendation panel')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant workspace e2e')
} finally {
  await browser.close()
}
