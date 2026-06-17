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

try {
  await page.goto(`${baseUrl}/ai-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('ai-assistant-shell').waitFor({ state: 'visible', timeout: 10000 })

  const shellColors = await page.evaluate(() => ({
    shell: getComputedStyle(document.querySelector('[data-testid="ai-assistant-shell"]')).backgroundColor,
    console: getComputedStyle(document.querySelector('[data-testid="ai-assistant-conversation-window"]')).backgroundColor,
  }))
  assert(isLightRgb(shellColors.shell), `Expected light shell background, got ${shellColors.shell}`)
  assert(isLightRgb(shellColors.console), `Expected light console background, got ${shellColors.console}`)

  await page.getByRole('button', { name: /New Run/i }).click()
  await page.getByTestId('ai-assistant-session-row').first().waitFor({ state: 'visible', timeout: 10000 })

  await page.getByPlaceholder('Message AI Assistant').fill('E2E echo inspector state')
  await page.getByTestId('ai-assistant-send').click()
  await page.getByText('Run completed', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('ai-assistant-tool-call-row').first().waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('ai-assistant-task-row').first().waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('ai-assistant-inspector-timeline').waitFor({ state: 'visible', timeout: 10000 })

  await page.getByPlaceholder('Message AI Assistant').fill('please update customer profile tier to gold')
  await page.getByTestId('ai-assistant-send').click()
  await page.getByText('Approval required', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('ai-assistant-approval-row').first().waitFor({ state: 'visible', timeout: 10000 })

  const pageMetrics = await page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    hasSessionList: Boolean(document.querySelector('[data-testid="ai-assistant-session-list"]')),
    hasRunInspector: Boolean(document.querySelector('[data-testid="ai-assistant-run-inspector"]')),
    hasEventCards: document.querySelectorAll('[data-testid="ai-assistant-event-card"]').length,
  }))
  assert(pageMetrics.overflowX <= 0, `Expected no horizontal overflow, got ${pageMetrics.overflowX}`)
  assert(pageMetrics.hasSessionList, 'Expected session list')
  assert(pageMetrics.hasRunInspector, 'Expected run inspector')
  assert(pageMetrics.hasEventCards >= 5, `Expected event cards, got ${pageMetrics.hasEventCards}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS ai assistant shell e2e')
} finally {
  await browser.close()
}
