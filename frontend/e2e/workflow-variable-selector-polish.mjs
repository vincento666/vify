import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function inputParameterColumnWidths(row) {
  return row.evaluate((element) => {
    const [nameCell, typeCell, valueCell] = Array.from(element.children)
    return [nameCell, typeCell, valueCell].map((cell) => Number(cell.getBoundingClientRect().width.toFixed(2)))
  })
}

function assertInputParameterRatio(widths, label) {
  const [nameWidth, typeWidth, valueWidth] = widths
  assert(typeWidth > 0, `${label} type column should have measurable width: ${widths.join(',')}`)
  const nameRatio = nameWidth / typeWidth
  const valueRatio = valueWidth / typeWidth
  assert(
    Math.abs(nameRatio - 2) <= 0.12,
    `${label} variable name/type width ratio should be 2:1, got widths ${widths.join(',')} ratio ${nameRatio.toFixed(2)}:1`,
  )
  assert(
    Math.abs(valueRatio - 3) <= 0.18,
    `${label} variable value/type width ratio should be 3:1, got widths ${widths.join(',')} ratio ${valueRatio.toFixed(2)}:1`,
  )
}

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `Variable selector polish ${Date.now()}`,
        description: 'connected upstream variable selector polish e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT', 'CONVERSATION_NAME'], ui: { position: { x: 140, y: 220 } } } },
          { nodeKey: 'llm_1', type: 'LLM', name: '大模型', config: { outputVariable: 'answer', ui: { position: { x: 520, y: 220 } } } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{llm_1.answer}}', ui: { position: { x: 900, y: 220 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create variable selector chatflow',
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()
  const panel = page.getByTestId('node-config-panel')
  const inputSection = panel.getByTestId('config-section-输入')
  await inputSection.getByRole('button', { name: '添加输入变量', exact: true }).click()

  const row = inputSection.getByTestId('input-parameter-row').first()
  const rowText = await row.innerText()
  assert(!rowText.includes('引用') && !rowText.includes('字面量'), `Input row must not expose reference/literal mode copy, got ${rowText}`)
  const valueControl = row.getByTestId('input-variable-value-control')
  await valueControl.waitFor({ state: 'visible', timeout: 5000 })
  assertInputParameterRatio(await inputParameterColumnWidths(row), 'Input parameter row')
  assert(await valueControl.getByTestId('input-variable-literal-input').count() === 1, 'Empty value left side should expose a direct text input')
  assert(await valueControl.getByRole('button', { name: '选择输入变量', exact: true }).count() === 1, 'Right side should always expose the variable picker button')
  await valueControl.getByTestId('input-variable-literal-input').fill('literal text')
  assert(await valueControl.getByTestId('input-variable-literal-input').inputValue() === 'literal text', 'Literal input should be directly editable from the left side')

  await valueControl.getByRole('button', { name: '选择输入变量', exact: true }).click()
  const picker = row.getByTestId('input-variable-picker')
  await picker.waitFor({ state: 'visible', timeout: 5000 })
  const pickerBox = await picker.boundingBox()
  const panelBox = await panel.boundingBox()
  const valueControlBox = await valueControl.boundingBox()
  assert(pickerBox && panelBox, 'Expected picker geometry')
  assert(valueControlBox, 'Expected value control geometry')
  assert(
    Math.abs(pickerBox.x - valueControlBox.x) <= 4,
    `Primary variable source picker should align with the parameter input x position, picker=${JSON.stringify(pickerBox)} valueControl=${JSON.stringify(valueControlBox)}`,
  )
  assert(
    pickerBox.y >= valueControlBox.y + valueControlBox.height - 2,
    `Primary variable source picker should open under the parameter input, picker=${JSON.stringify(pickerBox)} valueControl=${JSON.stringify(valueControlBox)}`,
  )
  assert(
    Math.abs(pickerBox.width - valueControlBox.width) <= 4,
    `Primary variable source picker should match the parameter input width, picker=${JSON.stringify(pickerBox)} valueControl=${JSON.stringify(valueControlBox)}`,
  )
  assert(pickerBox.x + pickerBox.width <= 1440 - 8, `Picker should remain inside the viewport, picker=${JSON.stringify(pickerBox)}`)
  assert(await picker.getByText('引用').count() === 0, 'Picker should not expose reference mode copy')
  assert(await picker.getByText('字面量').count() === 0, 'Picker should not expose literal mode copy')
  assert(await picker.locator('.variable-picker-columns').count() === 0, 'Coze-like picker should not render the old side-by-side columns')
  const sourceText = await picker.locator('[data-testid="input-variable-source-list"]').innerText()
  assert(sourceText.includes('开始'), `Expected default Chatflow source 开始, got ${sourceText}`)
  for (const staleSource of ['用户变量', '应用变量', '系统变量', '会话变量', '用户画像']) {
    assert(!sourceText.includes(staleSource), `Variable source list should not expose stale source ${staleSource}, got ${sourceText}`)
  }
  assert(!/\\b\\d+\\b/.test(sourceText), `Source list should omit variable counts, got ${sourceText}`)
  assert(await picker.locator('[data-testid="variable-source-arrow"]').count() >= 1, 'Expandable source list items should show a right chevron')
  assert(await picker.locator('.coze-variable-source-item .variable-source-icon, .coze-variable-source-item svg').count() === 0, 'Source list should not render heavy icons or SVG chevrons')
  assert(await picker.locator('.coze-variable-source-item small, .coze-variable-source-item em').count() === 0, 'Source list should not render secondary subtitles or count nodes')
  assert(await page.getByTestId('input-variable-flyout').count() === 0, 'Variable flyout should wait for source hover/click instead of opening by default')
  await panel.locator('.config-header').click()
  await picker.waitFor({ state: 'hidden', timeout: 5000 })
  assert(await row.getByTestId('input-variable-picker').count() === 0, 'Clicking outside the variable picker should close it')

  await valueControl.getByRole('button', { name: '选择输入变量', exact: true }).click()
  await picker.waitFor({ state: 'visible', timeout: 5000 })

  const startSource = picker.locator('[data-testid="input-variable-source-item"]', { hasText: '开始' })
  await startSource.hover()
  const flyout = page.getByTestId('input-variable-flyout')
  await flyout.waitFor({ state: 'visible', timeout: 5000 })
  assert((await flyout.getAttribute('data-placement')) === 'left', 'Input variable flyout should adapt left near the config panel edge')
  assert(await flyout.locator('.variable-item-header, .variable-option-main small, .variable-source-icon, svg').count() === 0, 'Variable flyout should only render variable names and type tags')
  const flyoutText = await flyout.innerText()
  assert(flyoutText.includes('USER_INPUT'), `Expected START USER_INPUT in flyout, got ${flyoutText}`)
  assert(flyoutText.includes('String'), `Expected full String type label in flyout, got ${flyoutText}`)
  assert(!flyoutText.includes('str.'), `Flyout should not use compact type labels, got ${flyoutText}`)
  assert(!flyoutText.includes('start.USER_INPUT'), `Flyout should not prefix node variables, got ${flyoutText}`)
  assert(!flyoutText.includes('sys.query'), `Default Chatflow picker should not expose sys.query, got ${flyoutText}`)
  const sourceBox = await startSource.boundingBox()
  const flyoutBox = await flyout.boundingBox()
  assert(sourceBox && flyoutBox, 'Expected flyout geometry after hover')
  assert(
    flyoutBox.width >= 224 && flyoutBox.width <= 272,
    `Variable flyout should stay compact and match the narrower picker rhythm, got ${JSON.stringify(flyoutBox)}`,
  )
  assert(flyoutBox.x + flyoutBox.width <= sourceBox.x + 1, `Left flyout should attach to source row center edge, source=${JSON.stringify(sourceBox)} flyout=${JSON.stringify(flyoutBox)}`)
  await flyout.locator('[data-testid="input-variable-option"]', { hasText: 'USER_INPUT' }).click()
  const chip = row.getByTestId('input-variable-chip')
  await chip.waitFor({ state: 'visible', timeout: 5000 })
  assert((await chip.innerText()).includes('USER_INPUT'), 'Expected selected START USER_INPUT chip')
  assert(await chip.locator('.variable-source-icon, svg, small').count() === 0, 'Selected chip should not render icons or reference/source descriptions')
  assert(await valueControl.getByTestId('input-variable-literal-input').count() === 0, 'Selected reference should replace the left input with a chip')
  assert(await valueControl.getByRole('button', { name: '选择输入变量', exact: true }).count() === 1, 'Right picker button should remain available after selecting a reference')
  await valueControl.getByRole('button', { name: '清除输入变量引用', exact: true }).click()
  await valueControl.getByTestId('input-variable-literal-input').fill('manual again')
  assert(await valueControl.getByTestId('input-variable-literal-input').inputValue() === 'manual again', 'Clearing the chip should restore manual input on the left')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log('PASS workflow variable selector polish')
} finally {
  await browser.close()
}
