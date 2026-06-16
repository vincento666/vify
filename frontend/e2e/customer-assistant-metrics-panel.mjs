import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function api(page, path) {
  return page.evaluate(
    async ({ path }) => {
      const response = await fetch(`/api/v1${path}`)
      return {
        ok: response.ok,
        status: response.status,
        body: await response.json(),
      }
    },
    { path },
  )
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })

  const storyStrip = page.getByTestId('customer-assistant-demo-stories')
  await storyStrip.getByText('退票 + 行李额并行').waitFor({ state: 'visible', timeout: 10000 })
  await storyStrip.getByRole('button', { name: /退票 \+ 行李额并行/ }).click()
  await page.getByText(/Session #/).waitFor({ state: 'visible', timeout: 10000 })

  const stories = await api(page, '/customer-assistant/demo-stories')
  assert(stories.ok, `Expected demo stories API success, got ${stories.status}`)
  const story = stories.body.data.list.find((item) => item.storyId === 'refund_baggage_parallel')
  assert(story, 'Expected seeded refund + baggage demo story')

  const metricsPanel = page.getByTestId('operator-metrics-panel')
  await metricsPanel.getByText('人工采纳率').waitFor({ state: 'visible', timeout: 10000 })
  let metrics = await api(page, `/customer-assistant/sessions/${story.sessionId}/metrics`)
  assert(metrics.ok, `Expected metrics API success, got ${metrics.status}`)
  assert(metrics.body.data.humanConfirmation.pending === 1, 'Expected one seeded pending action')
  assert(metrics.body.data.humanConfirmation.adoptionRate === 0, 'Expected zero adoption before confirmation')

  const refundTaskRow = page
    .getByTestId('operator-task-ledger')
    .locator('.task-row')
    .filter({ hasText: 'refund_ticket:MU5137-8899' })
    .first()
  await refundTaskRow.getByRole('button', { name: '取消' }).click()

  const actionPanel = page.getByTestId('operator-proposed-actions-panel')
  await actionPanel.getByText(/取消任务：refund_ticket:MU5137-8899/).waitFor({ state: 'visible', timeout: 10000 })
  const actionRow = actionPanel
    .locator('.action-row')
    .filter({ hasText: '取消任务：refund_ticket:MU5137-8899' })
    .first()
  await actionRow.getByRole('button', { name: '修改' }).click()
  await actionRow.getByLabel('修改拟议动作标题').fill('取消任务：refund_ticket:MU5137-8899（指标面板复核）')
  const payloadEditor = actionRow.getByLabel('修改拟议动作参数')
  const payload = JSON.parse(await payloadEditor.inputValue())
  payload.reason = 'metrics panel UAT edited reason'
  await payloadEditor.fill(JSON.stringify(payload, null, 2))
  await actionRow.getByRole('button', { name: '保存修改' }).click()
  await actionPanel.getByText('取消任务：refund_ticket:MU5137-8899（指标面板复核）').waitFor({
    state: 'visible',
    timeout: 10000,
  })

  const editedRow = actionPanel
    .locator('.action-row')
    .filter({ hasText: '指标面板复核' })
    .first()
  await editedRow.locator('button').filter({ hasText: '确认任务变更' }).click()
  await refundTaskRow.getByText('CANCELLED').waitFor({ state: 'visible', timeout: 10000 })
  await metricsPanel.getByText('100%').waitFor({ state: 'visible', timeout: 10000 })

  metrics = await api(page, `/customer-assistant/sessions/${story.sessionId}/metrics`)
  assert(metrics.body.data.humanConfirmation.pending === 1, 'Expected only the seeded action to remain pending')
  assert(metrics.body.data.humanConfirmation.adoptionRate === 1, 'Expected confirmed task command to count as adopted')
  const metricsText = await metricsPanel.innerText()
  assert(metricsText.includes('待确认动作'), 'Expected pending-action metric label')
  assert(!metricsText.includes('MU5137-8899'), 'Metrics panel must not render raw order ids')

  if (screenshotPath) {
    await metricsPanel.scrollIntoViewIfNeeded()
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant metrics panel e2e')
} finally {
  await browser.close()
}
