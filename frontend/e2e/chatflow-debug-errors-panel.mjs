import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '调试工具', exact: true }).click()
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.waitFor({ state: 'visible', timeout: 5000 })

  const title = dock.locator('.debug-dock-title strong')
  assert(await title.innerText() === '调试详情', 'Expected debug dock header title to be stable on error tab')

  await dock.getByRole('button', { name: '调试', exact: true }).click()
  assert(await title.innerText() === '调试详情', 'Expected debug dock header title to stay 调试详情 on debug tab')

  await dock.getByRole('button', { name: '错误列表', exact: true }).click()
  assert(await title.innerText() === '调试详情', 'Expected debug dock header title to stay 调试详情 after returning to error tab')

  const errorPanel = dock.getByTestId('debug-error-panel')
  await errorPanel.waitFor({ state: 'visible', timeout: 5000 })
  const emptyCard = errorPanel.locator('.debug-error-empty-card')
  await emptyCard.waitFor({ state: 'visible', timeout: 5000 })
  assert((await emptyCard.innerText()).includes('暂无错误'), 'Expected Coze-like empty error card')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow debug errors panel e2e')
} finally {
  await browser.close()
}
