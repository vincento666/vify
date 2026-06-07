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
  await toolbar.getByRole('button', { name: '添加节点', exact: true }).click()
  await page.getByTestId('bottom-node-palette').getByRole('button', { name: '大模型', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()

  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assert(await panel.getByText('节点名称', { exact: true }).count() === 0, 'Expected node name field removed')
  assert(await panel.getByRole('button', { name: '添加输入变量', exact: true }).count() === 1, 'Expected one input add button')

  const inputEditor = panel.getByTestId('input-parameter-editor')
  await inputEditor.getByRole('button', { name: '添加输入变量', exact: true }).click()
  const inputRow = inputEditor.getByTestId('input-parameter-row').first()
  await inputRow.waitFor({ state: 'visible', timeout: 5000 })
  const inputText = await inputRow.innerText()
  assert(inputText.includes('str.'), 'Expected compact input type label')
  assert(!inputText.includes('String'), 'Expected full input type label removed')
  const inputBox = await inputRow.boundingBox()
  assert(inputBox && inputBox.height <= 48, `Expected compact input row height, got ${inputBox?.height}`)

  const outputRow = panel.getByTestId('output-parameter-row').first()
  const outputText = await outputRow.innerText()
  assert(outputText.includes('str.'), 'Expected compact output type label')
  assert(!outputText.includes('String'), 'Expected full output type label removed')
  const outputBox = await outputRow.boundingBox()
  assert(outputBox && outputBox.height <= 44, `Expected compact output row height, got ${outputBox?.height}`)

  const textareaResize = await panel.locator('textarea').first().evaluate((el) => getComputedStyle(el).resize)
  assert(textareaResize === 'none', `Expected textarea resize none, got ${textareaResize}`)

  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })
  await toolbar.waitFor({ state: 'visible', timeout: 5000 })
  await toolbar.getByRole('button', { name: '添加节点', exact: true }).click()
  await page.getByTestId('bottom-node-palette').getByRole('button', { name: '消息', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="message_1"]').click()
  const messagePanel = page.locator('[data-testid="node-config-panel"]')
  await messagePanel.waitFor({ state: 'visible', timeout: 5000 })
  assert(await messagePanel.getByRole('switch', { name: '流式输出', exact: true }).count() === 1, 'Expected stream output switch')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow config compact e2e')
} finally {
  await browser.close()
}
