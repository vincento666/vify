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
  await page.locator('.canvas-actions').getByRole('button', { name: '对话试运行', exact: true }).click()
  const runPanel = page.getByTestId('test-run-panel')
  await runPanel.waitFor({ state: 'visible', timeout: 5000 })
  const runText = await runPanel.innerText()
  for (const forbidden of ['测试数据集', '关联应用', '调试应用', '查看日志', 'JSON模式', 'AI 补全', '保存并开始对话调试']) {
    assert(!runText.includes(forbidden), `Expected run panel to remove ${forbidden}`)
  }
  assert(runText.includes('对话试运行'), 'Expected chatflow run panel title')
  assert(runText.includes('对话设置'), 'Expected header settings action')
  assert(!runText.includes('运行参数'), 'Expected runtime fields removed from chat body')
  assert(await runPanel.getByRole('button', { name: '发送消息', exact: true }).count() === 1, 'Expected chat composer send action')

  await runPanel.getByRole('button', { name: '关闭试运行', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="end"]').click()
  const configPanel = page.getByTestId('node-config-panel')
  await configPanel.waitFor({ state: 'visible', timeout: 5000 })
  assert(await configPanel.getByRole('button', { name: '试运行当前节点', exact: true }).count() === 0, 'Expected End node test button hidden')
  assert(await configPanel.getByRole('button', { name: '更多节点操作', exact: true }).count() === 0, 'Expected no-op node action removed')

  await page.locator('.canvas-actions').getByRole('button', { name: '发布', exact: true }).click()
  const publishDialog = page.getByTestId('workflow-publish-dialog')
  await publishDialog.waitFor({ state: 'visible', timeout: 5000 })
  const publishText = await publishDialog.innerText()
  assert(!publishText.includes('发布应用'), 'Expected publish dialog not to use app-product wording')
  assert(!publishText.includes('调试应用'), 'Expected publish dialog not to expose debug app concept')
  assert(await page.getByTestId('workflow-ops-panel').count() === 0, 'Expected mixed ops panel to be removed')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow run panel cleanup e2e')
} finally {
  await browser.close()
}
