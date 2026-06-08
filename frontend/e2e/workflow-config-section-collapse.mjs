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
  const toolbar = page.getByTestId('canvas-bottom-toolbar')
  await toolbar.getByRole('button', { name: '添加节点', exact: true }).click()
  await page.getByTestId('bottom-node-palette').getByRole('button', { name: '大模型', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()

  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const inputSection = panel.getByTestId('config-section-输入')
  const inputHeader = inputSection.getByRole('button', { name: '输入', exact: true })
  await inputHeader.waitFor({ state: 'visible', timeout: 5000 })
  assert(await inputHeader.getAttribute('aria-expanded') === 'true', 'Expected input section expanded by default')
  await inputSection.getByTestId('input-parameter-editor').waitFor({ state: 'visible', timeout: 5000 })

  await inputHeader.click()
  assert(await inputHeader.getAttribute('aria-expanded') === 'false', 'Expected input section aria-expanded=false after collapse')
  await inputSection.getByTestId('input-parameter-editor').waitFor({ state: 'hidden', timeout: 5000 })

  await inputHeader.click()
  assert(await inputHeader.getAttribute('aria-expanded') === 'true', 'Expected input section aria-expanded=true after expand')
  await inputSection.getByTestId('input-parameter-editor').waitFor({ state: 'visible', timeout: 5000 })

  const outputSection = panel.getByTestId('config-section-输出')
  const outputHeader = outputSection.getByRole('button', { name: '输出', exact: true })
  await outputHeader.click()
  assert(await outputHeader.getAttribute('aria-expanded') === 'false', 'Expected output section to collapse')
  await outputSection.getByTestId('output-parameter-editor').waitFor({ state: 'hidden', timeout: 5000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow config section collapse e2e')
} finally {
  await browser.close()
}
