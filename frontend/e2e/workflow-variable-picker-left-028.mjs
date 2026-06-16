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
  const responseInput = editor.locator('textarea[aria-label="回答内容"]')
  await responseInput.fill('')
  await responseInput.focus()
  await responseInput.pressSequentially('{')

  const picker = editor.getByTestId('variable-picker')
  await picker.waitFor({ state: 'visible', timeout: 5000 })
  const pickerBox = await picker.boundingBox()
  const inputBox = await responseInput.boundingBox()
  assert(pickerBox && inputBox, 'Expected picker and input geometry')
  assert(await picker.getAttribute('data-picker-kind') === 'inline', 'Inline text picker should use the compact inline picker kind')
  assert(
    pickerBox.x >= inputBox.x - 8 && pickerBox.x <= inputBox.x + 24,
    `Inline variable picker should align with the inserted text area, picker=${JSON.stringify(pickerBox)} input=${JSON.stringify(inputBox)}`,
  )
  assert(
    pickerBox.y > inputBox.y + 20 && pickerBox.y < inputBox.y + 96,
    `Inline variable picker should appear below the inserted variable text, picker=${JSON.stringify(pickerBox)} input=${JSON.stringify(inputBox)}`,
  )
  assert(pickerBox.width <= inputBox.width - 16, `Inline variable picker should stay compact inside the text field width, picker=${JSON.stringify(pickerBox)} input=${JSON.stringify(inputBox)}`)
  assert(await picker.locator('.variable-picker-columns').count() === 0, 'Inline variable picker must not reuse the old two-column selector')
  assert(await picker.locator('.variable-source-item').count() === 0, 'Inline variable picker must not show the old source list')

  const search = picker.getByPlaceholder('搜索变量')
  await search.fill('output')
  const itemText = await picker.getByTestId('inline-variable-list').innerText()
  assert(itemText.includes('output'), `Search should filter local variable rows, got ${itemText}`)
  assert(!itemText.includes('{{'), `Inline variable picker must show compact variable labels instead of raw references, got ${itemText}`)
  assert(!itemText.includes('sys.query'), `Inline variable picker must not expose undeclared system variables, got ${itemText}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow inline variable suggestion 028')
} finally {
  await browser.close()
}
