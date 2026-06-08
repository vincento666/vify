import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Workflow LLM Resources ${Date.now()}`

try {
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('工作流名称').fill(name)

  const toolbar = page.locator('[data-testid="canvas-bottom-toolbar"]')
  await toolbar.getByRole('button', { name: '添加节点', exact: true }).click()
  const palette = page.locator('[data-testid="bottom-node-palette"]')
  await palette.getByRole('button', { name: '大模型', exact: true }).click()

  await page.locator('.coze-node', { hasText: '大模型' }).click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const resourceSection = panel.locator('[data-testid="llm-resource-section"]')
  await resourceSection.waitFor({ state: 'visible', timeout: 5000 })
  assert((await resourceSection.innerText()).includes('暂未配置技能'), 'Expected empty resource state before adding')

  await resourceSection.getByRole('button', { name: '添加资源', exact: true }).click()
  const skillTabs = resourceSection.locator('[data-testid="llm-skill-type-tabs"]')
  const knowledgeButton = resourceSection.locator('[data-testid="llm-skill-resource-list"] button', { hasText: '知识库检索' })
  const mcpTab = skillTabs.getByRole('tab', { name: 'MCP 工具', exact: true })
  assert(await knowledgeButton.isEnabled(), 'Expected Knowledge resource to be enabled')
  assert(await skillTabs.count() === 1, 'Expected resource type tabs to be visible')
  assert(await resourceSection.locator('[data-testid="workflow-resource-registry"]').count() === 0, 'Expected mixed registry dropdown to be absent')
  await mcpTab.click()
  assert(await mcpTab.getAttribute('aria-selected') === 'true', 'Expected MCP tab to become active')
  await skillTabs.getByRole('tab', { name: '知识库', exact: true }).click()

  await knowledgeButton.click()
  await resourceSection.locator('[data-testid="llm-resource-list"]').waitFor({ state: 'visible', timeout: 5000 })
  await resourceSection.locator('[aria-label="知识库 ID"]').fill('42')
  await resourceSection.locator('[aria-label="检索问题"]').fill('Lookup {{start.USER_INPUT}}')
  await resourceSection.locator('[aria-label="召回数量"]').fill('2')

  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForURL('**/workflows/*/canvas', { timeout: 10000 })
  await page.reload({ waitUntil: 'networkidle' })
  await page.locator('.coze-node', { hasText: '大模型' }).click()
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const persistedSection = panel.locator('[data-testid="llm-resource-section"]')
  await persistedSection.locator('[data-testid="llm-resource-list"]').waitFor({ state: 'visible', timeout: 5000 })

  assert(await persistedSection.locator('[aria-label="知识库 ID"]').inputValue() === '42', 'Expected knowledge id to persist')
  assert((await persistedSection.locator('[aria-label="检索问题"]').inputValue()).includes('{{start.USER_INPUT}}'), 'Expected knowledge query to persist')
  assert((await persistedSection.innerText()).includes('运行时会检索并注入模型上下文'), 'Expected runtime support status to be visible')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow LLM resource context e2e')
} finally {
  await browser.close()
}
