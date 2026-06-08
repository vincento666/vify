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
  await page.getByPlaceholder('Chatflow 名称').fill(`Chatflow Debug ${Date.now()}`)
  await page.getByRole('button', { name: '对话试运行', exact: true }).click()

  const panel = page.locator('[data-testid="test-run-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const panelText = await panel.innerText()
  for (const label of ['对话试运行', '运行参数', '猜你想问']) {
    assert(panelText.includes(label), `Expected chatflow run surface to include ${label}`)
  }
  for (const label of ['保存本次输入', '开始试运行', '查看日志', '对话流入参配置', '测试数据集', '关联应用', 'JSON模式', 'AI 补全', '保存并开始对话调试']) {
    assert(!panelText.includes(label), `Expected chatflow run surface to remove ${label}`)
  }

  const toolbar = page.locator('[data-testid="canvas-bottom-toolbar"]')
  await toolbar.getByRole('button', { name: '调试工具', exact: true }).click()
  const dock = page.locator('[data-testid="workflow-debug-dock"]')
  await dock.waitFor({ state: 'visible', timeout: 5000 })
  assert((await dock.innerText()).includes('错误列表'), 'Expected bottom debug dock to stay available')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow debug polish e2e')
} finally {
  await browser.close()
}
