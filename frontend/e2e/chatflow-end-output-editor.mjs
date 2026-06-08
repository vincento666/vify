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
  await page.locator('.vue-flow__node[data-id="end"]').click()
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assert(await panel.getByTestId('config-section-输入').count() === 0, 'END panel must not expose input parameters section')

  const returnModeSection = panel.getByTestId('end-return-mode-section')
  await returnModeSection.waitFor({ state: 'visible', timeout: 5000 })
  assert(await returnModeSection.getByRole('button', { name: '返回文本', exact: true }).count() === 1, 'END return mode must be panel-level')
  assert(await returnModeSection.getByRole('button', { name: '返回变量', exact: true }).count() === 1, 'END return mode must include 返回变量')

  const outputSection = panel.getByTestId('config-section-输出')
  assert(await outputSection.getByTestId('end-response-editor').count() === 0, 'END return mode tabs must not be inside 输出 section')
  const outputEditor = outputSection.getByTestId('output-parameter-editor')
  await outputEditor.waitFor({ state: 'visible', timeout: 5000 })
  assert(await outputEditor.getByLabel('输出格式').count() === 1, 'END output editor must expose output format selector')
  assert(await outputEditor.getByLabel('回答内容').count() === 0, 'END answer content must not be nested in 输出 section')
  assert(await outputEditor.getByRole('button', { name: '添加输出变量', exact: true }).count() === 1, 'Expected one END output add button in text mode')
  assert((await outputEditor.locator('.output-column-row').innerText()).includes('变量值'), 'END output variables must expose a value mapping column')

  const answerSection = panel.getByTestId('config-section-回答内容')
  await answerSection.waitFor({ state: 'visible', timeout: 5000 })
  assert(await answerSection.getByLabel('回答内容').count() === 1, 'END answer content section must expose answer textarea')
  assert(await answerSection.getByLabel('流式输出').count() === 1, 'END answer content section must expose stream switch')
  const answerTextarea = answerSection.getByLabel('回答内容')
  await answerTextarea.fill('{{')
  const inlinePicker = answerSection.getByTestId('variable-picker')
  await inlinePicker.waitFor({ state: 'visible', timeout: 5000 })
  assert(await inlinePicker.locator('.variable-source-icon, svg, small').count() === 0, 'Inline variable picker should not render icons or descriptions')
  const inlinePickerText = await inlinePicker.innerText()
  assert(inlinePickerText.includes('sys.query'), `END answer inline picker should expose upstream start query, got ${inlinePickerText}`)
  assert(!inlinePickerText.includes('{{'), `Inline variable picker should omit reference paths, got ${inlinePickerText}`)
  await answerTextarea.fill('112')

  let rows = outputEditor.getByTestId('output-parameter-row')
  assert(await rows.count() === 1, 'END output section must default to one output variable row')
  let row = rows.first()
  assert(await row.getByLabel('输出变量名').inputValue() === 'output', 'END default output variable must be output')
  const deleteButton = row.getByRole('button', { name: '删除输出变量', exact: true })
  assert(await deleteButton.isEnabled(), 'END default output variable should be manually deletable')
  await deleteButton.click()
  assert(await rows.count() === 0, 'END output section should allow deleting the default output variable')

  await outputEditor.getByRole('button', { name: '添加输出变量', exact: true }).click()
  rows = outputEditor.getByTestId('output-parameter-row')
  assert(await rows.count() === 1, 'END output add button should restore one output variable row')
  row = rows.first()
  assert(await row.getByLabel('输出变量名').inputValue() === 'output', 'END first added output variable should be output')
  assert(await row.getByRole('button', { name: '选择输出变量值', exact: true }).count() === 1, 'END output variable row must have a value reference control')
  await row.getByRole('button', { name: '选择输出变量值', exact: true }).click()
  const outputPicker = row.getByTestId('output-variable-picker')
  await outputPicker.waitFor({ state: 'visible', timeout: 5000 })
  await outputPicker.locator('[data-testid="output-variable-source-item"]', { hasText: '开始' }).click()
  const outputPickerText = await outputPicker.locator('[data-testid="output-variable-item-list"]').innerText()
  assert(outputPickerText.includes('sys.query'), `Expected END output picker to expose upstream start query, got ${outputPickerText}`)
  await outputPicker.locator('[data-testid="output-variable-option"]', { hasText: 'sys.query' }).click()
  const outputChipText = await row.locator('[data-testid="output-variable-chip"]').innerText()
  assert(outputChipText.includes('sys.query'), `Expected END output value chip after choosing upstream variable, got ${outputChipText}`)
  const rowBox = await row.boundingBox()
  assert(rowBox && rowBox.height <= 52, `Expected compact END output variable row, got ${rowBox?.height}`)

  await returnModeSection.getByRole('button', { name: '返回变量', exact: true }).click()
  assert(await panel.getByTestId('config-section-回答内容').count() === 0, 'END variable return mode should hide answer content section')
  assert(await outputEditor.getByTestId('output-parameter-row').count() === 1, 'END variable return mode should keep output variable settings')

  await page.getByRole('button', { name: '关闭配置', exact: true }).click()
  await page.getByTestId('canvas-bottom-toolbar').getByRole('button', { name: '添加节点', exact: true }).click()
  await page.getByTestId('bottom-node-palette').getByRole('button', { name: '大模型', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()

  const llmEditor = panel.getByTestId('output-parameter-editor')
  await llmEditor.waitFor({ state: 'visible', timeout: 5000 })
  assert(await llmEditor.getByLabel('输出格式').count() === 1, 'Non-END output editor should keep output format selector')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow END output editor e2e')
} finally {
  await browser.close()
}
