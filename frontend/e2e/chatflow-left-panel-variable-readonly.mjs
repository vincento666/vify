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
  const variablePanel = page.getByTestId('chatflow-variable-panel')
  await variablePanel.waitFor({ state: 'visible', timeout: 5000 })

  const configPanelBefore = await page.getByTestId('node-config-panel').count()
  assert(configPanelBefore === 0, `Create canvas should start without an open node config panel, got ${configPanelBefore}`)

  await variablePanel.getByText('{{sys.query}}', { exact: true }).click()
  await page.waitForTimeout(200)

  const configPanelAfter = await page.getByTestId('node-config-panel').count()
  assert(
    configPanelAfter === 0,
    `Left settings variables must be readonly and must not auto-select END config, got panel count ${configPanelAfter}`,
  )

  const endNodeText = await page.locator('.vue-flow__node[data-id="end"]').innerText()
  assert(
    !endNodeText.includes('sys.query'),
    `Left settings variables must not mutate END node content, got END text ${JSON.stringify(endNodeText)}`,
  )

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow left panel variable readonly e2e')
} finally {
  await browser.close()
}
