import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function selectOption(page, label) {
  await page.locator('.el-select-dropdown__item', { hasText: label }).last().click()
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Workflow Output Params ${Date.now()}`

try {
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('工作流名称').fill(name)
  await page.getByRole('button', { name: '添加节点' }).click()
  await page.locator('.node-palette button', { hasText: '大模型' }).click()
  await page.locator('.coze-node', { hasText: '大模型' }).click()

  let panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  let editor = panel.locator('[data-testid="output-parameter-editor"]')
  await editor.waitFor({ state: 'visible', timeout: 5000 })

  await editor.locator('.output-format-row .el-select').click()
  await selectOption(page, 'Markdown')
  await editor.getByRole('button', { name: '添加输出变量' }).click()

  let rows = editor.locator('[data-testid="output-parameter-row"]')
  assert(await rows.count() === 2, 'Expected output editor to add a second output row')
  await rows.nth(0).getByPlaceholder('变量名').fill('answer')
  await rows.nth(1).getByPlaceholder('变量名').fill('answer')

  const duplicateError = await editor.locator('.output-parameter-errors').innerText()
  assert(duplicateError.includes('输出变量 answer 重复'), 'Expected duplicate output variable validation')

  await rows.nth(1).getByPlaceholder('变量名').fill('reasoning')
  await rows.nth(1).locator('.el-select').click()
  await selectOption(page, 'obj.')

  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForURL('**/workflows/*/canvas', { timeout: 10000 })
  await page.reload({ waitUntil: 'networkidle' })
  await page.locator('.coze-node', { hasText: '大模型' }).click()

  panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  editor = panel.locator('[data-testid="output-parameter-editor"]')
  rows = editor.locator('[data-testid="output-parameter-row"]')

  assert((await editor.locator('.output-format-row').innerText()).includes('Markdown'), 'Expected output format to persist')
  assert(await rows.count() === 2, 'Expected output parameter rows to persist after reopen')
  assert(await rows.nth(0).getByPlaceholder('变量名').inputValue() === 'answer', 'Expected first output variable to persist')
  assert(await rows.nth(1).getByPlaceholder('变量名').inputValue() === 'reasoning', 'Expected second output variable to persist')
  assert((await rows.nth(1).innerText()).includes('obj.'), 'Expected output variable type to persist')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow output parameter editor e2e')
} finally {
  await browser.close()
}
