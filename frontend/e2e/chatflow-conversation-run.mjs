import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Chatflow Run ${Date.now()}`

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('Chatflow 名称').fill(name)
  await page.locator('.coze-node', { hasText: '结束' }).click()
  const configPanel = page.locator('[data-testid="node-config-panel"]')
  await configPanel.waitFor({ state: 'visible', timeout: 5000 })
  await configPanel
    .getByPlaceholder('返回给调用方的文本，可使用变量引用')
    .fill('机器人收到 {{sys.query}} via {{sys.channel}} for {{global.brand}}/{{global.locale}}')

  await page.getByRole('button', { name: '对话试运行' }).click()
  const testPanel = page.locator('[data-testid="test-run-panel"]')
  await testPanel.waitFor({ state: 'visible', timeout: 5000 })
  await testPanel.getByTestId('chatflow-run-fields-toggle').click()
  await testPanel.getByPlaceholder('发送消息').fill('查订单')
  await testPanel.getByPlaceholder('conversation_id').fill('conv-e2e')
  await testPanel.getByPlaceholder('user_id').fill('user-e2e')
  await testPanel.getByRole('button', { name: '发送消息', exact: true }).click()
  await page.waitForURL('**/chatflows/*/canvas', { timeout: 10000 })
  await testPanel.getByTestId('chatflow-assistant-message').waitFor({ state: 'visible', timeout: 10000 })

  const assistantText = await testPanel.getByTestId('chatflow-assistant-message').innerText()
  assert(
    assistantText.includes('机器人收到 查订单 via web for Hify/zh-CN'),
    `Expected assistant-style output to render sys variables, got: ${assistantText}`,
  )
  assert(
    await testPanel.getByTestId('chatflow-typewriter-message').count() === 0,
    'Expected completed chatflow run not to keep a blinking typewriter caret',
  )
  assert(
    await testPanel.getByRole('button', { name: '重置会话', exact: true }).count() === 1,
    'Expected chatflow run panel to expose reset session button',
  )
  assert(
    await testPanel.locator('.chatflow-composer-shell').getByRole('button', { name: '发送消息', exact: true }).count() === 1,
    'Expected send button to be embedded inside the message input shell',
  )
  const profileHeights = await testPanel.locator('.chatflow-profile-grid .run-input-field').evaluateAll((fields) =>
    fields.map((field) => {
      const control = field.querySelector('.el-input__wrapper, .el-select__wrapper')
      return control ? Math.round(control.getBoundingClientRect().height) : 0
    }),
  )
  assert(
    new Set(profileHeights.filter(Boolean)).size === 1,
    `Expected run parameter controls to share the same height, got ${profileHeights.join(',')}`,
  )

  await page.locator('.coze-node.node-start').click()
  await page.getByTestId('node-config-panel').waitFor({ state: 'visible', timeout: 5000 })
  assert(await testPanel.count() === 0, 'Expected clicking a node to replace chatflow run panel with node config panel')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow conversation run e2e')
} finally {
  await browser.close()
}
