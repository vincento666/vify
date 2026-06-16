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

  await page.getByLabel('坐席侧内部追问').fill('退票和行李额可以并行处理吗？')
  await page.getByRole('button', { name: /追问助手/ }).click()
  await page
    .getByTestId('operator-recommendation-panel')
    .getByText(/执行写操作前分别确认/)
    .waitFor({ state: 'visible', timeout: 10000 })

  const refundTaskRow = page
    .getByTestId('operator-task-ledger')
    .locator('.task-row')
    .filter({ hasText: 'refund_ticket:MU5137-8899' })
    .first()
  await refundTaskRow.getByRole('button', { name: '取消' }).click()
  const actionPanel = page.getByTestId('operator-proposed-actions-panel')
  await actionPanel.getByText(/取消任务：refund_ticket:MU5137-8899/).waitFor({ state: 'visible', timeout: 10000 })
  const cancelActionRow = actionPanel
    .locator('.action-row')
    .filter({ hasText: '取消任务：refund_ticket:MU5137-8899' })
    .first()
  await cancelActionRow.locator('button').filter({ hasText: '确认任务变更' }).click()
  await refundTaskRow.getByText('CANCELLED').waitFor({ state: 'visible', timeout: 10000 })

  await storyStrip.getByRole('button', { name: /发票申请中途切航班动态/ }).click()
  await page.getByText(/Session #/).waitFor({ state: 'visible', timeout: 10000 })
  const invoiceTaskRow = page
    .getByTestId('operator-task-ledger')
    .locator('.task-row')
    .filter({ hasText: 'invoice_apply:CA1301-20231027-8899' })
    .first()
  await invoiceTaskRow.getByRole('button', { name: '恢复' }).waitFor({ state: 'visible', timeout: 10000 })

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
