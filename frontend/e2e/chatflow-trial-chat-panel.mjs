import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const runResponses = []

page.on('response', async (response) => {
  if (response.url().includes('/api/v1/chatflows/') && response.url().includes('/runs')) {
    runResponses.push(response.status())
  }
})

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })

  const toolbar = page.locator('[data-testid="canvas-bottom-toolbar"]')
  await toolbar.waitFor({ state: 'visible', timeout: 5000 })
  assert(await toolbar.getByRole('button', { name: '适应画布', exact: true }).count() === 0, 'Expected fit-view toolbar button removed')

  await page.getByRole('button', { name: '对话试运行', exact: true }).click()
  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })

  await panel.getByTestId('chatflow-run-chat-window').waitFor({ state: 'visible', timeout: 5000 })
  assert((await panel.getByText('保存本次输入').count()) === 0, 'Expected saved-input checkbox removed')
  assert((await panel.getByRole('button', { name: '开始试运行', exact: true }).count()) === 0, 'Expected form-style run button removed')

  const fieldsToggle = panel.getByTestId('chatflow-run-fields-toggle')
  await fieldsToggle.waitFor({ state: 'visible', timeout: 5000 })
  assert(await panel.getByPlaceholder('conversation_id').count() === 0, 'Expected run fields collapsed by default')
  await fieldsToggle.click()
  await panel.getByPlaceholder('conversation_id').waitFor({ state: 'visible', timeout: 5000 })

  await panel.getByTestId('chatflow-opening-message').waitFor({ state: 'visible', timeout: 5000 })
  const suggestions = panel.getByTestId('chatflow-guide-question')
  assert(await suggestions.count() >= 1, 'Expected suggested questions')
  await suggestions.first().click()

  await page.waitForURL('**/chatflows/*/canvas', { timeout: 10000 })
  await panel.getByTestId('chatflow-user-message').waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByTestId('chatflow-assistant-message').waitFor({ state: 'visible', timeout: 10000 })
  assert(!runResponses.includes(500), `Expected no 500 run response, got ${runResponses.join(',')}`)

  const composer = panel.getByPlaceholder('输入消息')
  await composer.fill('查退款')
  const composerBox = await composer.evaluate((element) => ({
    scrollHeight: element.scrollHeight,
    clientHeight: element.clientHeight,
    overflowY: window.getComputedStyle(element).overflowY,
  }))
  assert(
    composerBox.scrollHeight <= composerBox.clientHeight + 2 || composerBox.overflowY === 'hidden',
    `Expected single-line composer without visible scrollbar, got ${JSON.stringify(composerBox)}`,
  )
  await panel.getByRole('button', { name: '发送消息', exact: true }).click()
  await panel.getByTestId('chatflow-assistant-message').waitFor({ state: 'visible', timeout: 10000 })
  assert(await panel.getByTestId('chatflow-suggested-questions').count() === 0, 'Expected suggested questions hidden after first message')
  assert(!runResponses.includes(500), `Expected no 500 run response after composer send, got ${runResponses.join(',')}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow trial chat panel e2e')
} finally {
  await browser.close()
}
