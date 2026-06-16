import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function api(page, path, options = {}) {
  return page.evaluate(
    async ({ path, options }) => {
      const response = await fetch(`/api/v1${path}`, {
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
        ...options,
      })
      return {
        ok: response.ok,
        status: response.status,
        body: await response.json(),
      }
    },
    { path, options },
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
  await cancelActionRow.getByRole('button', { name: '修改' }).click()

  const editedTitle = '取消任务：refund_ticket:MU5137-8899（坐席已复核）'
  await cancelActionRow.getByLabel('修改拟议动作标题').fill(editedTitle)
  const payloadEditor = cancelActionRow.getByLabel('修改拟议动作参数')
  const payload = JSON.parse(await payloadEditor.inputValue())
  payload.reason = 'browser UAT edited reason'
  payload.operatorReviewed = true
  await payloadEditor.fill(JSON.stringify(payload, null, 2))
  await cancelActionRow.getByRole('button', { name: '保存修改' }).click()

  await actionPanel.getByText(editedTitle).waitFor({ state: 'visible', timeout: 10000 })
  const editedRow = actionPanel.locator('.action-row').filter({ hasText: editedTitle }).first()
  const editedRowText = await editedRow.innerText()
  assert(editedRowText.includes('"operatorReviewed":true'), 'Expected edited payload to stay visible in action row')
  assert(editedRowText.includes('PENDING'), 'Expected edited action to remain pending before confirmation')
  assert(
    await editedRow.locator('button').filter({ hasText: '执行动作' }).isDisabled(),
    'Task command actions must keep execute disabled before confirmation',
  )

  await editedRow.locator('button').filter({ hasText: '确认任务变更' }).click()
  await refundTaskRow.getByText('CANCELLED').waitFor({ state: 'visible', timeout: 10000 })

  const events = await api(page, `/customer-assistant/sessions/${story.sessionId}/events`)
  assert(events.ok, `Expected event API success, got ${events.status}`)
  const eventTypes = events.body.data.list.map((event) => event.type)
  assert(eventTypes.includes('proposed_action_modified'), 'Expected action modification audit event')
  assert(eventTypes.includes('proposed_task_command_confirmed'), 'Expected edited action confirmation audit event')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant proposed action edit workbench e2e')
} finally {
  await browser.close()
}
