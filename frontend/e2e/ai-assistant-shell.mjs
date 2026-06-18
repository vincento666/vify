import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const beforeCleanupScreenshotPath = process.env.HIFY_E2E_BEFORE_CLEANUP_SCREENSHOT
const openRouterApiKey = process.env.HIFY_AI_ASSISTANT_OPENROUTER_API_KEY || ''

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

async function installDeterministicHarnessRouteIfNeeded() {
  if (openRouterApiKey) return
  await page.route('**/api/v1/ai-assistant/sessions/*/messages/async', async (route) => {
    const request = route.request()
    const payload = JSON.parse(request.postData() || '{}')
    payload.modelMode = 'deterministic'
    delete payload.modelConfig
    if (payload.message?.includes('echo_context')) {
      payload.toolName = 'echo_context'
      payload.toolInput = { echo: 'E2E 检查回显与任务面板' }
    }
    if (payload.message?.includes('update_customer_profile')) {
      payload.toolName = 'update_customer_profile'
      payload.toolInput = { customerId: 'ui-customer', patch: { tier: 'gold' } }
    }
    await route.continue({
      headers: { ...request.headers(), 'content-type': 'application/json' },
      postData: JSON.stringify(payload),
    })
  })
}

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

async function configureLiveModelIfNeeded() {
  if (!openRouterApiKey) return
  await page.getByTestId('ai-assistant-model-config-icon').click()
  await page.getByTestId('ai-assistant-model-base-url').fill('https://openrouter.ai/api/v1')
  await page.getByTestId('ai-assistant-model-api-key').fill(openRouterApiKey)
}

async function latestRunHeader() {
  const headers = page.getByTestId('ai-assistant-run-event-group-header')
  await headers.last().waitFor({ state: 'visible', timeout: 10000 })
  return headers.last()
}

async function expandLatestRun() {
  const header = await latestRunHeader()
  if ((await header.getAttribute('aria-expanded')) === 'false') {
    await header.click()
  }
  return header
}

try {
  await installDeterministicHarnessRouteIfNeeded()
  await page.goto(`${baseUrl}/ai-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('ai-assistant-shell').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('ai-assistant-composer').waitFor({ state: 'visible', timeout: 10000 })
  await configureLiveModelIfNeeded()

  const shellColors = await page.evaluate(() => ({
    shell: getComputedStyle(document.querySelector('[data-testid="ai-assistant-shell"]')).backgroundColor,
    console: getComputedStyle(document.querySelector('[data-testid="ai-assistant-conversation-window"]')).backgroundColor,
  }))
  assert(isLightRgb(shellColors.shell), `Expected light shell background, got ${shellColors.shell}`)
  assert(isLightRgb(shellColors.console), `Expected light console background, got ${shellColors.console}`)

  const sessionIdsBeforeCreate = await listSessionIds()
  const initialSessionRows = await page.getByTestId('ai-assistant-session-row').count()
  await page.getByTestId('ai-assistant-new-session').click()
  await page.getByTestId('ai-assistant-session-row').first().waitFor({ state: 'visible', timeout: 10000 })
  const createdSessionRows = await page.getByTestId('ai-assistant-session-row').count()
  assert(createdSessionRows >= initialSessionRows, 'Expected a visible session after creating one')
  const sessionIdsAfterCreate = await listSessionIds()
  const createdSessionId = sessionIdsAfterCreate.find((id) => !sessionIdsBeforeCreate.includes(id)) || sessionIdsAfterCreate[0]

  await submitPrompt('请必须调用 echo_context 工具，回显“E2E 检查回显与任务面板”。')
  await page.getByTestId('ai-assistant-run-final-answer').last().waitFor({
    state: 'visible',
    timeout: 45000,
  })
  const firstHeaderText = await (await latestRunHeader()).textContent()
  assert(firstHeaderText.includes('已处理'), `Expected compact completed header, got ${firstHeaderText}`)
  assert(!firstHeaderText.includes('任务记录 #'), `Expected no task record id in header, got ${firstHeaderText}`)
  assert(!firstHeaderText.includes('E2E 检查回显'), `Expected no prompt text in header, got ${firstHeaderText}`)
  await page.getByTestId('ai-assistant-user-message').last().waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('ai-assistant-tool-call-row').first().waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('ai-assistant-task-row').first().waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('ai-assistant-inspector-timeline').waitFor({ state: 'visible', timeout: 10000 })

  await expandLatestRun()
  const firstCardState = await page.evaluate(() => {
    const header = document.querySelector('[data-testid="ai-assistant-event-card-header"]')
    const before = header?.getAttribute('aria-expanded') || ''
    header?.click()
    return { before, count: document.querySelectorAll('[data-testid="ai-assistant-event-card-header"]').length }
  })
  assert(firstCardState.count > 0, 'Expected event card headers after expanding the run')
  assert(firstCardState.before === 'false', 'Expected event cards to default collapsed')
  await page.waitForFunction(
    () => Boolean(document.querySelector('[data-testid="ai-assistant-event-card-header"][aria-expanded="true"]')),
    undefined,
    { timeout: 10000 },
  )

  await submitPrompt('请必须调用 update_customer_profile 工具，把客户 ui-customer 的等级更新为 gold，需要审批。')
  await page.getByTestId('ai-assistant-event-stream').getByText('需要审批', { exact: true }).first().waitFor({
    state: 'visible',
    timeout: 45000,
  })
  const finalAnswerCountBeforeApproval = await page.getByTestId('ai-assistant-run-final-answer').count()
  await expandLatestRun()
  const approvalEventHeader = page.getByTestId('ai-assistant-event-card-header').filter({ hasText: '需要审批' }).last()
  await approvalEventHeader.waitFor({ state: 'visible', timeout: 10000 })
  if ((await approvalEventHeader.getAttribute('aria-expanded')) === 'false') {
    await approvalEventHeader.click()
  }
  const approveButtons = page.locator('.ai-event__actions button').filter({ hasText: '批准' })
  await approveButtons.last().click()
  await page.waitForFunction(
    (count) => document.querySelectorAll('[data-testid="ai-assistant-run-final-answer"]').length > count,
    finalAnswerCountBeforeApproval,
    { timeout: 45000 },
  )
  await page.getByTestId('ai-assistant-tool-call-row').first().waitFor({ state: 'visible', timeout: 10000 })

  const pageMetrics = await page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    overflowY: document.documentElement.scrollHeight - window.innerHeight,
    hasSessionList: Boolean(document.querySelector('[data-testid="ai-assistant-session-list"]')),
    hasRunInspector: Boolean(document.querySelector('[data-testid="ai-assistant-run-inspector"]')),
    hasEventCards: document.querySelectorAll('[data-testid="ai-assistant-event-card"]').length,
    hasUserMessages: document.querySelectorAll('[data-testid="ai-assistant-user-message"]').length,
    hasFinalAnswers: document.querySelectorAll('[data-testid="ai-assistant-run-final-answer"]').length,
    taskRecordHeaders: Array.from(document.querySelectorAll('[data-testid="ai-assistant-run-event-group-header"]')).filter((header) =>
      header.textContent.includes('任务记录 #'),
    ).length,
    composerVisible: Boolean(document.querySelector('[data-testid="ai-assistant-composer"]')?.getBoundingClientRect().height),
    composerBottom: document.querySelector('[data-testid="ai-assistant-composer"]')?.getBoundingClientRect().bottom || 0,
  }))
  assert(pageMetrics.overflowX <= 0, `Expected no horizontal overflow, got ${pageMetrics.overflowX}`)
  assert(pageMetrics.overflowY <= 2, `Expected no page-level vertical overflow, got ${pageMetrics.overflowY}`)
  assert(pageMetrics.hasSessionList, 'Expected session list')
  assert(pageMetrics.hasRunInspector, 'Expected run inspector')
  assert(pageMetrics.hasEventCards >= 5, `Expected event cards, got ${pageMetrics.hasEventCards}`)
  assert(pageMetrics.hasUserMessages >= 2, `Expected user message bubbles, got ${pageMetrics.hasUserMessages}`)
  assert(pageMetrics.hasFinalAnswers >= 2, `Expected final answer bubbles, got ${pageMetrics.hasFinalAnswers}`)
  assert(pageMetrics.taskRecordHeaders === 0, `Expected compact run headers, got ${pageMetrics.taskRecordHeaders} old headers`)
  assert(pageMetrics.composerVisible, 'Expected composer visible inside one-screen shell')
  assert(pageMetrics.composerBottom <= 900, `Expected composer inside viewport, got bottom ${pageMetrics.composerBottom}`)

  if (beforeCleanupScreenshotPath) {
    await page.screenshot({ path: beforeCleanupScreenshotPath, fullPage: true })
  }

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
  assert((await page.getByTestId('ai-assistant-user-message').count()) === 0, 'Expected user messages cleared')

  const deleteResponse = page.waitForResponse((response) => {
    return response.request().method() === 'DELETE' && /\/api\/v1\/ai-assistant\/sessions\/\d+$/.test(response.url())
  })
  await page
    .getByTestId('ai-assistant-session-row')
    .filter({ hasText: `会话 #${createdSessionId}` })
    .getByTestId('ai-assistant-delete-session')
    .click()
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
