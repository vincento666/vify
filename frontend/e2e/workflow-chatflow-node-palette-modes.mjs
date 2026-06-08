import { mkdir } from 'node:fs/promises'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function paletteLabels(page) {
  const toolbar = page.getByTestId('canvas-bottom-toolbar')
  await toolbar.waitFor({ state: 'visible', timeout: 5000 })
  await toolbar.getByRole('button', { name: '添加节点', exact: true }).click()
  const palette = page.getByTestId('bottom-node-palette')
  await palette.waitFor({ state: 'visible', timeout: 5000 })
  return palette.evaluate((element) => Array.from(element.querySelectorAll('button')).map((button) => button.getAttribute('aria-label') || button.textContent?.trim() || ''))
}

async function saveScreenshot(page, name) {
  if (!screenshotDir) return
  await mkdir(screenshotDir, { recursive: true })
  await page.screenshot({ path: `${screenshotDir}/${name}.png`, fullPage: true })
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })
  const workflowLabels = await paletteLabels(page)
  for (const label of ['大模型', '工作流', 'API 调用', '智能体', '变量聚合', '人工输入', '知识库检索']) {
    assert(workflowLabels.includes(label), `Workflow palette should include ${label}: ${workflowLabels.join(',')}`)
  }
  for (const label of ['消息', '问题', '信息收集', '转人工']) {
    assert(!workflowLabels.includes(label), `Workflow palette should hide conversation-only node ${label}: ${workflowLabels.join(',')}`)
  }
  await saveScreenshot(page, 'workflow-node-palette')

  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  const chatflowLabels = await paletteLabels(page)
  for (const label of ['大模型', '智能体', '消息', '问题', '信息收集', '转人工', '变量聚合']) {
    assert(chatflowLabels.includes(label), `Chatflow palette should include ${label}: ${chatflowLabels.join(',')}`)
  }
  await saveScreenshot(page, 'chatflow-node-palette')

  console.log('PASS workflow chatflow node palette modes e2e')
} finally {
  await browser.close()
}
