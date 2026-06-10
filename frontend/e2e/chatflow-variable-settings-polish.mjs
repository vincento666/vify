import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } })

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  const panel = page.getByTestId('chatflow-variable-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })

  const conversationSection = panel.getByTestId('chatflow-variable-scope-conversation')
  await conversationSection.waitFor({ state: 'visible', timeout: 5000 })
  const conversationToggle = conversationSection.locator('.chatflow-variable-scope-toggle')
  assert((await conversationToggle.getAttribute('aria-expanded')) === 'false', 'Conversation variables should be collapsed by default')
  assert(await conversationSection.getByRole('button', { name: '新增会话变量', exact: true }).count() === 0, 'Collapsed conversation section should hide add button')
  assert(!(await conversationSection.getByText('试运行、API 或渠道调用时随会话注入').isVisible()), 'Collapsed conversation section should hide description')
  assert(await conversationSection.getByTestId('chatflow-resource-variable').count() === 0, 'Collapsed conversation section should hide variable rows')

  await conversationToggle.click()
  assert((await conversationToggle.getAttribute('aria-expanded')) === 'true', 'Conversation variables should expand')
  assert(await conversationSection.getByRole('button', { name: '新增会话变量', exact: true }).count() === 1, 'Expanded conversation section should show add button on the header row')
  assert(await conversationSection.getByText('试运行、API 或渠道调用时随会话注入').isVisible(), 'Expanded conversation section should show description')
  assert(await conversationSection.getByTestId('chatflow-resource-variable').count() >= 1, 'Expanded conversation section should show variable rows')

  await conversationSection.getByRole('button', { name: '新增会话变量', exact: true }).click()
  const newRows = conversationSection.getByTestId('chatflow-resource-variable')
  const latest = newRows.last()
  await latest.getByRole('textbox', { name: '会话变量 key', exact: true }).fill('customer_level')
  await latest.getByRole('textbox', { name: '会话变量显示名', exact: true }).fill('客户等级')
  assert(await latest.getByRole('textbox', { name: '会话变量 key', exact: true }).inputValue() === 'customer_level', 'Expected added conversation variable key')
  assert(await latest.getByRole('textbox', { name: '会话变量显示名', exact: true }).inputValue() === '客户等级', 'Expected added conversation variable label')

  const userSection = panel.getByTestId('chatflow-variable-scope-user')
  await userSection.locator('.chatflow-variable-scope-toggle').click()
  assert(await userSection.getByRole('button', { name: '新增用户变量', exact: true }).isEnabled(), 'User variable add button should be enabled')

  if (screenshotPath) await page.screenshot({ path: screenshotPath, fullPage: true })
  console.log('PASS chatflow variable settings polish e2e')
} finally {
  await browser.close()
}
