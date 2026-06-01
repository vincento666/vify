import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Workflow Publish ${Date.now()}`

try {
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('工作流名称').fill(name)
  await page.getByRole('button', { name: '发布' }).click()

  const opsPanel = page.locator('[data-testid="workflow-ops-panel"]')
  await opsPanel.waitFor({ state: 'visible', timeout: 5000 })
  let opsText = await opsPanel.innerText()
  assert(opsText.includes('画布校验未通过'), 'Expected publish to be blocked by validation errors')

  await page.getByRole('button', { name: '快速连线' }).click()
  opsText = await opsPanel.innerText()
  assert(opsText.includes('需要先完成一次成功试运行'), 'Expected publish to require a successful test run')

  await page.getByRole('button', { name: '试运行' }).click()
  const testPanel = page.locator('[data-testid="test-run-panel"]')
  await testPanel.waitFor({ state: 'visible', timeout: 5000 })
  await testPanel.getByPlaceholder('输入 userMessage').fill('hello publish gate')
  await testPanel.getByRole('button', { name: '运行', exact: true }).click()
  await page.waitForURL('**/workflows/*/canvas', { timeout: 10000 })
  await testPanel.locator('[data-testid="workflow-run-output"]').waitFor({ state: 'visible', timeout: 10000 })

  await page.getByRole('button', { name: '发布' }).click()
  await opsPanel.waitFor({ state: 'visible', timeout: 5000 })
  await opsPanel.getByRole('button', { name: '确认发布' }).click()
  await opsPanel.getByText('PUBLISHED').waitFor({ state: 'visible', timeout: 10000 })

  await opsPanel.getByRole('button', { name: 'Open API' }).click()
  opsText = await opsPanel.innerText()
  assert(opsText.includes('/api/v1/workflows/'), 'Expected Open API tab to show workflow run endpoint')
  assert(opsText.includes('userMessage'), 'Expected Open API tab to show request sample')

  await opsPanel.getByRole('button', { name: '运行观测' }).click()
  opsText = await opsPanel.innerText()
  assert(opsText.includes('SUCCEEDED'), 'Expected observe tab to show latest successful run status')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow publish/open-api/observe e2e')
} finally {
  await browser.close()
}
