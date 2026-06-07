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

  const inputState = await responseInput.evaluate((element) => ({
    value: element.value,
    selectionStart: element.selectionStart,
    selectionEnd: element.selectionEnd,
  }))
  assert(inputState.value === '{{}}', `Typing { should auto-complete to {{}}, got ${inputState.value}`)
  assert(inputState.selectionStart === 2 && inputState.selectionEnd === 2, `Caret must be inside braces, got ${JSON.stringify(inputState)}`)

  const picker = editor.getByTestId('variable-picker')
  await picker.waitFor({ state: 'visible', timeout: 5000 })
  await responseInput.press('Escape')
  await picker.waitFor({ state: 'hidden', timeout: 5000 })

  await responseInput.fill('{{}}')
  await responseInput.evaluate((element) => element.setSelectionRange(element.value.length, element.value.length))
  await responseInput.press('Backspace')
  await responseInput.press('Backspace')
  await responseInput.press('Backspace')
  const afterRightToLeftDelete = await responseInput.inputValue()
  assert(afterRightToLeftDelete === '{', `Deleting {{}} from right to left must leave a deletable single brace, got ${afterRightToLeftDelete}`)

  await responseInput.fill('')
  await responseInput.focus()
  await responseInput.pressSequentially('{')
  await picker.waitFor({ state: 'visible', timeout: 5000 })
  const pickerText = await picker.innerText()
  assert(pickerText.includes('output'), `Inline picker should expose local END output variable, got ${pickerText}`)
  assert(!pickerText.includes('{{'), `Inline picker must show compact variable labels instead of raw references, got ${pickerText}`)
  assert(!pickerText.includes('sys.query'), `Inline picker must not expose undeclared system variables directly, got ${pickerText}`)
  await picker.getByTestId('variable-option').filter({ hasText: 'output' }).click()
  const selectedValue = await responseInput.inputValue()
  assert(selectedValue === '{{output}}', `Selected local variable should replace {{}}, got ${selectedValue}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow inline variable trigger 028')
} finally {
  await browser.close()
}
