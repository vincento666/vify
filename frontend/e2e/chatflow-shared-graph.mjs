import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function bodyText(page) {
  return page.locator('body').innerText()
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Chatflow E2E ${Date.now()}`

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  await page.getByPlaceholder('Chatflow 名称').fill(name)
  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForURL('**/chatflows/*/canvas', { timeout: 10000 })
  await page.reload({ waitUntil: 'networkidle' })

  let text = await bodyText(page)
  const reopenedName = await page.getByPlaceholder('Chatflow 名称').inputValue()
  assert(reopenedName === name, 'Expected reopened Chatflow canvas to show saved name')
  assert(text.includes('sys.query'), 'Expected default Chatflow START variables to persist')
  assert(text.includes('sys.conversation_id'), 'Expected conversation identity variable to persist')
  assert(text.includes('对话设置'), 'Expected Chatflow canvas to show conversation settings panel')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  await page.goto(`${baseUrl}/chatflows`, { waitUntil: 'networkidle' })
  text = await bodyText(page)
  assert(text.includes(name), 'Expected Chatflow list to include saved Chatflow')

  await page.goto(`${baseUrl}/workflows`, { waitUntil: 'networkidle' })
  text = await bodyText(page)
  assert(!text.includes(name), 'Expected Workflow list to exclude Chatflow resources')

  console.log('PASS chatflow shared graph e2e')
} finally {
  await browser.close()
}
