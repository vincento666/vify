import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })

  const toolbar = page.locator('[data-testid="canvas-bottom-toolbar"]')
  await toolbar.waitFor({ state: 'visible', timeout: 5000 })
  for (const label of ['缩小显示比例', '放大显示比例', '自动布局', '鼠标模式', '添加节点', '调试工具', '试运行']) {
    assert(await toolbar.getByRole('button', { name: label, exact: true }).count() === 1, `Expected toolbar button ${label}`)
  }
  assert(await toolbar.getByRole('button', { name: '适应画布', exact: true }).count() === 0, 'Expected fit-view toolbar button removed')
  assert(await toolbar.getByRole('button', { name: '画布面板', exact: true }).count() === 0, 'Expected duplicate hide-all canvas panel button to be removed')
  assert(await toolbar.getByRole('button', { name: '角色', exact: true }).count() === 0, 'Expected unused role toolbar button to be removed')
  assert((await toolbar.getByRole('button', { name: '试运行', exact: true }).evaluate((el) => getComputedStyle(el).backgroundColor)).includes('34'), 'Expected toolbar run button to be green')

  await toolbar.getByRole('button', { name: '鼠标模式', exact: true }).click()
  assert(await toolbar.getByRole('button', { name: '触控板模式', exact: true }).count() === 1, 'Expected operation mode toggle to switch aria label')

  await toolbar.getByRole('button', { name: '调试工具', exact: true }).click()
  const debugDock = page.locator('[data-testid="workflow-debug-dock"]')
  await debugDock.waitFor({ state: 'visible', timeout: 5000 })
  const dockText = await debugDock.innerText()
  assert(dockText.includes('错误列表') && dockText.includes('调试'), 'Expected debug dock tabs')
  await debugDock.getByRole('button', { name: '关闭调试工具', exact: true }).click()
  await debugDock.waitFor({ state: 'hidden', timeout: 5000 })

  await toolbar.getByRole('button', { name: '添加节点', exact: true }).click()
  const palette = page.locator('[data-testid="bottom-node-palette"]')
  await palette.waitFor({ state: 'visible', timeout: 5000 })
  const paletteText = await palette.innerText()
  assert(await palette.getByPlaceholder('搜索节点').count() === 1, 'Expected add-node palette search')
  assert(paletteText.includes('大模型') && paletteText.includes('知识库检索'), 'Expected grouped add-node palette')
  await palette.getByRole('button', { name: '大模型', exact: true }).click()

  await page.locator('.coze-node', { hasText: '大模型' }).click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const panelText = await panel.innerText()
  assert(panelText.includes('单次'), 'Expected LLM panel to keep single-run mode visible')
  assert(await panel.getByRole('button', { name: '试运行当前节点', exact: true }).count() === 1, 'Expected LLM header run icon')
  assert(await panel.getByTestId('llm-model-section').count() === 1, 'Expected LLM model section')
  assert(await panel.getByTestId('llm-resource-section').count() === 1, 'Expected LLM resource section')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow panel polish e2e')
} finally {
  await browser.close()
}
