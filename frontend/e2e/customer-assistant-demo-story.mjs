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

  const storyStrip = page.getByTestId('customer-assistant-demo-stories')
  await storyStrip.waitFor({ state: 'visible', timeout: 10000 })
  await storyStrip.getByText('退票 + 行李额并行').waitFor({ state: 'visible', timeout: 10000 })

  await storyStrip.getByRole('button', { name: /退票 \+ 行李额并行/ }).click()
  await page.getByText(/Session #/).waitFor({ state: 'visible', timeout: 10000 })

  const customerLane = await page.getByTestId('customer-conversation-lane').innerText()
  assert(customerLane.includes('我要退 MU5137 的票'), 'Expected seeded opening message in customer lane')

  const taskLedger = await page.getByTestId('operator-task-ledger').innerText()
  assert(taskLedger.includes('refund_ticket:MU5137-8899'), 'Expected seeded refund task in ledger')
  assert(taskLedger.includes('baggage_service:MU5137-8899'), 'Expected seeded baggage task in ledger')

  const proposedActions = await page.getByTestId('operator-proposed-actions-panel').innerText()
  assert(proposedActions.includes('并行处理退票与行李额确认'), 'Expected seeded proposed action in panel')

  const stripText = await storyStrip.innerText()
  assert(stripText.includes('1 待确认'), 'Expected story picker to expose pending action count')

  const pageMetrics = await page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    selectedStoryVisible: document.body.textContent.includes('赵女士'),
  }))
  assert(pageMetrics.overflowX <= 0, `Expected no horizontal overflow, got ${pageMetrics.overflowX}`)
  assert(pageMetrics.selectedStoryVisible, 'Expected selected story customer metadata')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant demo story e2e')
} finally {
  await browser.close()
}
