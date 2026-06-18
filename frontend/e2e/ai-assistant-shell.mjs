import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function isLightRgb(value) {
  const match = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/)
  if (!match) return false
  const [, r, g, b] = match.map(Number)
  return (r + g + b) / 3 >= 230
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

async function listSessionIds() {
  return page.evaluate(async () => {
    const response = await fetch('/api/v1/ai-assistant/sessions')
    const payload = await response.json()
    return payload.data.list.map((session) => session.id)
  })
}

async function submitPrompt(text) {
  await page.getByPlaceholder('输入给 AI 助手的消息').fill(text)
  const responsePromise = page.waitForResponse((response) => {
    return response.url().includes('/api/v1/ai-assistant/sessions/') && response.url().includes('/messages')
  })
  await page.getByTestId('ai-assistant-send').click()
  const response = await responsePromise
  assert(response.ok(), `Expected message POST to succeed, got ${response.status()}`)
}

try {
  await page.goto(`${baseUrl}/ai-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('ai-assistant-shell').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('ai-assistant-composer').waitFor({ state: 'visible', timeout: 10000 })

  const shellColors = await page.evaluate(() => ({
    shell: getComputedStyle(document.querySelector('[data-testid="ai-assistant-shell"]')).backgroundColor,
    console: getComputedStyle(document.querySelector('[data-testid="ai-assistant-conversation-window"]')).backgroundColor,
  }))
  assert(isLightRgb(shellColors.shell), `Expected light shell background, got ${shellColors.shell}`)
  assert(isLightRgb(shellColors.console), `Expected light console background, got ${shellColors.console}`)

  const initialSessionRows = await page.getByTestId('ai-assistant-session-row').count()
  await page.getByTestId('ai-assistant-new-session').click()
  await page.getByTestId('ai-assistant-session-row').first().waitFor({ state: 'visible', timeout: 10000 })
  const createdSessionRows = await page.getByTestId('ai-assistant-session-row').count()
  assert(createdSessionRows >= initialSessionRows, 'Expected a visible session after creating one')
  const createdSessionId = (await listSessionIds())[0]

  await submitPrompt('请必须调用 echo_context 工具，回显“E2E 检查回显与任务面板”。')
  await page.getByTestId('ai-assistant-event-stream').getByText('运行完成', { exact: true }).first().waitFor({
    state: 'visible',
    timeout: 10000,
  })
  const firstRunId = await page.getByTestId('ai-assistant-run-row').first().getAttribute('aria-pressed')
  assert(firstRunId === 'true', 'Expected the first completed run to be selected')
  await page.getByTestId('ai-assistant-tool-call-row').first().waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('ai-assistant-task-row').first().waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('ai-assistant-inspector-timeline').waitFor({ state: 'visible', timeout: 10000 })

  const firstCardHeader = page.getByTestId('ai-assistant-event-card-header').first()
  assert((await firstCardHeader.getAttribute('aria-expanded')) === 'false', 'Expected event cards to default collapsed')
  await firstCardHeader.click()
  assert((await firstCardHeader.getAttribute('aria-expanded')) === 'true', 'Expected event card header to expand details')
  await page.getByTestId('ai-assistant-stream-toggle').click()
  const restoreEcho = page.getByTestId('ai-assistant-event-stream').getByRole('button', { name: '展开回显' })
  await restoreEcho.waitFor({ state: 'visible', timeout: 10000 })
  await restoreEcho.click()

  await submitPrompt('请必须调用 update_customer_profile 工具，把客户 ui-customer 的等级更新为 gold，需要审批。')
  await page.getByTestId('ai-assistant-event-stream').getByText('需要审批', { exact: true }).first().waitFor({
    state: 'visible',
    timeout: 10000,
  })
  await page.getByTestId('ai-assistant-approval-row').first().waitFor({ state: 'visible', timeout: 10000 })
  assert((await page.getByTestId('ai-assistant-run-row').count()) >= 2, 'Expected multiple run rows after two prompts')
  await page.getByTestId('ai-assistant-run-row').nth(1).click()
  await page.getByTestId('ai-assistant-tool-call-row').first().waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('ai-assistant-run-row').first().click()
  await page.getByTestId('ai-assistant-approval-row').first().waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('ai-assistant-approval-row').first().getByRole('button', { name: '批准' }).click()
  await page.getByTestId('ai-assistant-event-stream').getByText('运行完成', { exact: true }).first().waitFor({
    state: 'visible',
    timeout: 10000,
  })
  assert((await page.getByTestId('ai-assistant-approval-row').count()) === 0, 'Expected pending approvals to clear')
  await page.getByTestId('ai-assistant-approval-history-row').first().waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('ai-assistant-tool-call-row').first().waitFor({ state: 'visible', timeout: 10000 })

  const pageMetrics = await page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    overflowY: document.documentElement.scrollHeight - window.innerHeight,
    hasSessionList: Boolean(document.querySelector('[data-testid="ai-assistant-session-list"]')),
    hasRunInspector: Boolean(document.querySelector('[data-testid="ai-assistant-run-inspector"]')),
    hasEventCards: document.querySelectorAll('[data-testid="ai-assistant-event-card"]').length,
    composerVisible: Boolean(document.querySelector('[data-testid="ai-assistant-composer"]')?.getBoundingClientRect().height),
    composerBottom: document.querySelector('[data-testid="ai-assistant-composer"]')?.getBoundingClientRect().bottom || 0,
  }))
  assert(pageMetrics.overflowX <= 0, `Expected no horizontal overflow, got ${pageMetrics.overflowX}`)
  assert(pageMetrics.overflowY <= 2, `Expected no page-level vertical overflow, got ${pageMetrics.overflowY}`)
  assert(pageMetrics.hasSessionList, 'Expected session list')
  assert(pageMetrics.hasRunInspector, 'Expected run inspector')
  assert(pageMetrics.hasEventCards >= 5, `Expected event cards, got ${pageMetrics.hasEventCards}`)
  assert(pageMetrics.composerVisible, 'Expected composer visible inside one-screen shell')
  assert(pageMetrics.composerBottom <= 900, `Expected composer inside viewport, got bottom ${pageMetrics.composerBottom}`)

  const clearResponse = page.waitForResponse((response) => {
    return response.url().includes('/api/v1/ai-assistant/sessions/') && response.url().endsWith('/history')
  })
  await page.getByTestId('ai-assistant-clear-history').click()
  assert((await clearResponse).ok(), 'Expected clear history request to succeed')
  await page.getByTestId('ai-assistant-event-stream').getByText('空闲', { exact: true }).waitFor({
    state: 'visible',
    timeout: 10000,
  })
  assert((await page.getByTestId('ai-assistant-event-card').count()) === 0, 'Expected event cards cleared')

  const deleteResponse = page.waitForResponse((response) => {
    return response.request().method() === 'DELETE' && /\/api\/v1\/ai-assistant\/sessions\/\d+$/.test(response.url())
  })
  await page.getByTestId('ai-assistant-session-row').first().getByTestId('ai-assistant-delete-session').click()
  assert((await deleteResponse).ok(), 'Expected delete session request to succeed')
  const sessionIdsAfterDelete = await listSessionIds()
  assert(!sessionIdsAfterDelete.includes(createdSessionId), 'Expected deleted session to disappear')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS ai assistant shell e2e')
} finally {
  await browser.close()
}
