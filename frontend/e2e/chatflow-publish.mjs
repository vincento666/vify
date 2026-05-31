import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Chatflow Publish ${Date.now()}`

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('Chatflow 名称').fill(name)
  await page.getByPlaceholder('可插入 {{sys.query}} 等变量').fill('发布测试 {{sys.query}}')
  await page.getByPlaceholder('输入用户消息').fill('hello publish')

  const publishShell = page.locator('[data-testid="chatflow-publish-shell"]')
  await publishShell.waitFor({ state: 'visible', timeout: 5000 })
  let shellText = await publishShell.innerText()
  assert(shellText.includes('需要先完成一次成功试运行'), 'Expected publish shell to block before test run')
  assert(shellText.includes('/api/v1/chatflows/'), 'Expected publish shell to expose Chatflow Open API endpoint')
  assert(shellText.includes('CHATFLOW'), 'Expected publish shell to show resource type')

  await page.getByRole('button', { name: '发送测试消息' }).click()
  await page.waitForURL('**/chatflows/*/canvas', { timeout: 10000 })
  await page.locator('.message-bubble.assistant').waitFor({ state: 'visible', timeout: 10000 })
  shellText = await publishShell.innerText()
  assert(shellText.includes('SUCCEEDED'), 'Expected publish shell to show successful run status')

  await publishShell.getByRole('button', { name: '发布 Chatflow' }).click()
  await publishShell.getByText('PUBLISHED').waitFor({ state: 'visible', timeout: 10000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow publish/open shell e2e')
} finally {
  await browser.close()
}
