import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'load' })
  await page.locator('.coze-node.node-end').click()

  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })

  const editor = panel.getByTestId('config-section-回答内容').getByTestId('end-answer-content-editor')
  await editor.waitFor({ state: 'visible', timeout: 5000 })

  const responseInput = editor.locator('textarea[aria-label="回答内容"]')
  await responseInput.fill('')
  await responseInput.focus()
  await responseInput.pressSequentially('{')

  const picker = editor.getByTestId('variable-picker')
  await picker.waitFor({ state: 'visible', timeout: 5000 })

  const option = picker.getByTestId('variable-option').filter({ hasText: 'output' }).first()
  await option.waitFor({ state: 'visible', timeout: 5000 })

  const metrics = await option.evaluate((element) => {
    const optionRect = element.getBoundingClientRect()
    const name = element.querySelector('.variable-option-main strong')
    const badge = element.querySelector('.variable-type-badge')
    const nameRect = name?.getBoundingClientRect()
    const badgeRect = badge?.getBoundingClientRect()
    const nameStyle = name ? window.getComputedStyle(name) : null
    return {
      optionWidth: optionRect.width,
      nameText: name?.textContent?.trim() || '',
      nameWidth: nameRect?.width || 0,
      nameClientWidth: name?.clientWidth || 0,
      nameScrollWidth: name?.scrollWidth || 0,
      nameTextOverflow: nameStyle?.textOverflow || '',
      nameOverflow: nameStyle?.overflow || '',
      badgeText: badge?.textContent?.trim() || '',
      badgeWidth: badgeRect?.width || 0,
      badgeLeft: badgeRect?.left || 0,
      nameRight: nameRect?.right || 0,
    }
  })

  assert(metrics.nameText === 'output', `Expected local variable name output, got ${JSON.stringify(metrics)}`)
  assert(metrics.badgeText === 'String', `Expected full type label String, got ${JSON.stringify(metrics)}`)
  assert(metrics.nameTextOverflow !== 'ellipsis', `Inline variable names should not use ellipsis styling: ${JSON.stringify(metrics)}`)
  assert(metrics.nameScrollWidth <= metrics.nameClientWidth + 1, `Variable name should not be ellipsized: ${JSON.stringify(metrics)}`)
  assert(metrics.badgeWidth <= 5 * 16, `Variable type badge should be compact, got ${JSON.stringify(metrics)}`)
  assert(metrics.badgeLeft >= metrics.nameRight + 0.25 * 16, `Type badge should sit after the variable name, got ${JSON.stringify(metrics)}`)

  await page.getByRole('button', { name: '关闭配置', exact: true }).click()
  await page.getByTestId('canvas-bottom-toolbar').getByRole('button', { name: '添加节点', exact: true }).click()
  await page.getByTestId('bottom-node-palette').getByRole('button', { name: '大模型', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()

  const llmInputEditor = panel.getByTestId('input-parameter-editor')
  await llmInputEditor.waitFor({ state: 'visible', timeout: 5000 })
  await llmInputEditor.getByRole('button', { name: '添加输入变量', exact: true }).click()
  const llmInputRow = llmInputEditor.getByTestId('input-parameter-row').last()
  await llmInputRow.getByLabel('输入变量名').fill('input_1')

  const llmSystemSection = panel.getByTestId('config-section-系统提示词')
  await llmSystemSection.waitFor({ state: 'visible', timeout: 5000 })
  const systemPrompt = llmSystemSection.locator('textarea')
  await systemPrompt.fill('')
  await systemPrompt.focus()
  await systemPrompt.pressSequentially('{')

  const llmPicker = llmSystemSection.getByTestId('variable-picker')
  await llmPicker.waitFor({ state: 'visible', timeout: 5000 })
  const llmOption = llmPicker.getByTestId('variable-option').filter({ hasText: 'input_1' }).first()
  await llmOption.waitFor({ state: 'visible', timeout: 5000 })

  const llmMetrics = await llmOption.evaluate((element) => {
    const optionRect = element.getBoundingClientRect()
    const name = element.querySelector('.variable-option-main strong')
    const badge = element.querySelector('.variable-type-badge')
    const main = element.querySelector('.variable-option-main')
    const nameRect = name?.getBoundingClientRect()
    const badgeRect = badge?.getBoundingClientRect()
    const mainRect = main?.getBoundingClientRect()
    const nameStyle = name ? window.getComputedStyle(name) : null
    const style = badge ? window.getComputedStyle(badge) : null
    return {
      optionWidth: optionRect.width,
      mainWidth: mainRect?.width || 0,
      nameText: name?.textContent?.trim() || '',
      nameWidth: nameRect?.width || 0,
      nameClientWidth: name?.clientWidth || 0,
      nameScrollWidth: name?.scrollWidth || 0,
      nameTextOverflow: nameStyle?.textOverflow || '',
      nameOverflow: nameStyle?.overflow || '',
      badgeText: badge?.textContent?.trim() || '',
      badgeWidth: badgeRect?.width || 0,
      badgeLeft: badgeRect?.left || 0,
      nameRight: nameRect?.right || 0,
      badgeDisplay: style?.display || '',
    }
  })

  assert(llmMetrics.nameText === 'input_1', `Expected LLM local variable name input_1, got ${JSON.stringify(llmMetrics)}`)
  assert(llmMetrics.badgeText === 'String', `Expected full type label String, got ${JSON.stringify(llmMetrics)}`)
  assert(llmMetrics.nameTextOverflow !== 'ellipsis', `LLM inline variable names should not use ellipsis styling: ${JSON.stringify(llmMetrics)}`)
  assert(llmMetrics.nameScrollWidth <= llmMetrics.nameClientWidth + 1, `LLM variable name should not be ellipsized: ${JSON.stringify(llmMetrics)}`)
  assert(llmMetrics.badgeWidth <= 5 * 16, `LLM variable type badge should be compact, got ${JSON.stringify(llmMetrics)}`)
  assert(llmMetrics.mainWidth <= llmMetrics.nameWidth + llmMetrics.badgeWidth + 1.25 * 16, `Inline option main area should shrink to content, got ${JSON.stringify(llmMetrics)}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow inline variable option layout')
} finally {
  await browser.close()
}
