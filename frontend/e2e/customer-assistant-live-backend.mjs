import { mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const calls = []

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function rememberApiCall(request) {
  const url = request.url()
  if (!url.includes('/api/v1/customer-assistant/')) return
  calls.push({
    method: request.method(),
    url,
    body: request.postDataJSON?.(),
  })
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
page.on('request', rememberApiCall)

try {
  await page.goto(`${baseUrl}/customer-assistant`, { waitUntil: 'networkidle' })
  await page.getByTestId('customer-assistant-workspace').waitFor({ state: 'visible', timeout: 10000 })

  await page.getByText('尚未创建会话').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('operator-task-empty-state').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('button', { name: '模拟客户输入' }).click()

  await page.getByText(/Session #\d+/).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('operator-task-ledger').getByText('refund_ticket').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('operator-task-ledger').getByText('WAITING').waitFor({ state: 'visible', timeout: 10000 })
  await page
    .getByTestId('operator-recommendation-panel')
    .getByText('refund_ticket worker WAITING')
    .waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText(/缺失：.*订单号/).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('operator-draft-panel').getByText(/订单号/).waitFor({ state: 'visible', timeout: 10000 })

  assert(calls.some((call) => call.method === 'POST' && call.url.endsWith('/sessions')), 'Expected live session call')
  const turnCall = calls.find((call) => call.method === 'POST' && /\/sessions\/\d+\/turns$/.test(call.url))
  assert(turnCall, 'Expected live turn call')
  assert(turnCall.body.message === '我要退票', `Expected message payload, got ${JSON.stringify(turnCall.body)}`)
  assert(turnCall.body.idempotencyKey, 'Expected idempotency key in turn payload')
  assert(calls.some((call) => call.method === 'GET' && /\/sessions\/\d+\/tasks$/.test(call.url)), 'Expected live task refresh')
  assert(calls.some((call) => call.method === 'GET' && /\/sessions\/\d+\/events$/.test(call.url)), 'Expected live event refresh')

  if (screenshotPath) {
    mkdirSync(dirname(screenshotPath), { recursive: true })
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS customer assistant live backend e2e')
} finally {
  page.off('request', rememberApiCall)
  await browser.close()
}
