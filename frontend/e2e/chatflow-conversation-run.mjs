import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Chatflow Run ${Date.now()}`

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('Chatflow 名称').fill(name)
  await page.getByPlaceholder('可插入 {{sys.query}} 等变量').fill('机器人收到 {{sys.query}} via {{sys.channel}}')
  await page.getByPlaceholder('输入用户消息').fill('查订单')
  await page.getByPlaceholder('conversation_id').fill('conv-e2e')
  await page.getByPlaceholder('user_id').fill('user-e2e')

  await page.getByRole('button', { name: '发送测试消息' }).click()
  await page.waitForURL('**/chatflows/*/canvas', { timeout: 10000 })
  await page.locator('.message-bubble.assistant').waitFor({ state: 'visible', timeout: 10000 })

  const assistantText = await page.locator('.message-bubble.assistant').innerText()
  assert(
    assistantText.includes('机器人收到 查订单 via web'),
    `Expected assistant-style output to render sys variables, got: ${assistantText}`,
  )

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow conversation run e2e')
} finally {
  await browser.close()
}
