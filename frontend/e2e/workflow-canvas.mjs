import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function assertText(page, text) {
  const body = await page.locator('body').innerText()
  assert(body.includes(text), `Expected page body to include: ${text}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Workflow Canvas ${Date.now()}`

try {
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('工作流名称').fill(name)
  await assertText(page, '添加节点')
  await assertText(page, '开始')
  await assertText(page, '结束')

  await page.getByRole('button', { name: '添加节点' }).click()
  await assertText(page, 'API 调用')
  await page.locator('.node-palette button', { hasText: '大模型' }).click()
  await page.locator('.coze-node', { hasText: '大模型' }).waitFor({ state: 'visible', timeout: 5000 })
  await assertText(page, '大模型')

  const llmTitle = page.getByText('大模型').first()
  const box = await llmTitle.boundingBox()
  assert(box, 'Expected LLM node title to be visible')
  await page.mouse.move(box.x + 20, box.y + 12)
  await page.mouse.down()
  await page.mouse.move(box.x + 120, box.y + 82, { steps: 8 })
  await page.mouse.up()

  await page.getByRole('button', { name: '快速连线' }).click()
  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForURL('**/workflows/*/canvas', { timeout: 10000 })
  const canvasUrl = page.url()

  await page.reload({ waitUntil: 'networkidle' })
  const reopenedName = await page.getByPlaceholder('工作流名称').inputValue()
  assert(reopenedName === name, 'Expected saved workflow name to reopen in the canvas title input')
  await assertText(page, '大模型')
  await assertText(page, 'str.output')
  await assertText(page, '已保存')
  assert(page.url() === canvasUrl, 'Expected saved canvas to reopen on the same detail route')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS workflow canvas save and reopen e2e ${canvasUrl}`)
} finally {
  await browser.close()
}
