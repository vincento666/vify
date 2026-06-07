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
    return {
      optionWidth: optionRect.width,
      nameText: name?.textContent?.trim() || '',
      nameWidth: nameRect?.width || 0,
      nameClientWidth: name?.clientWidth || 0,
      nameScrollWidth: name?.scrollWidth || 0,
      badgeText: badge?.textContent?.trim() || '',
      badgeWidth: badgeRect?.width || 0,
      badgeLeft: badgeRect?.left || 0,
      nameRight: nameRect?.right || 0,
    }
  })

  assert(metrics.nameText === 'output', `Expected local variable name output, got ${JSON.stringify(metrics)}`)
  assert(metrics.badgeText === 'String', `Expected full type label String, got ${JSON.stringify(metrics)}`)
  assert(metrics.nameScrollWidth <= metrics.nameClientWidth + 1, `Variable name should not be ellipsized: ${JSON.stringify(metrics)}`)
  assert(metrics.badgeWidth <= 5 * 16, `Variable type badge should be compact, got ${JSON.stringify(metrics)}`)
  assert(metrics.badgeLeft >= metrics.nameRight + 0.25 * 16, `Type badge should sit after the variable name, got ${JSON.stringify(metrics)}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow inline variable option layout')
} finally {
  await browser.close()
}
