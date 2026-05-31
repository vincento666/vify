import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Workflow Config ${Date.now()}`

try {
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('工作流名称').fill(name)
  await page.getByRole('button', { name: '添加节点' }).click()
  await page.locator('.node-palette button', { hasText: '大模型' }).click()
  await page.locator('.coze-node', { hasText: '大模型' }).click()
  await page.locator('[data-testid="node-config-panel"]').waitFor({ state: 'visible', timeout: 5000 })

  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.locator('input').nth(0).fill('意图识别')
  await panel.locator('textarea').fill('请识别 {{start.USER_INPUT}} 的用户意图')
  await panel.locator('input').nth(1).fill('intent')

  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForURL('**/workflows/*/canvas', { timeout: 10000 })
  await page.reload({ waitUntil: 'networkidle' })

  await page.locator('.coze-node', { hasText: '意图识别' }).click()
  await page.locator('[data-testid="node-config-panel"]').waitFor({ state: 'visible', timeout: 5000 })
  const promptValue = await panel.locator('textarea').inputValue()
  const outputValue = await panel.locator('input').nth(1).inputValue()

  assert(promptValue.includes('{{start.USER_INPUT}}'), 'Expected prompt config to persist after reopen')
  assert(outputValue === 'intent', 'Expected output variable config to persist after reopen')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow node config panel e2e')
} finally {
  await browser.close()
}
