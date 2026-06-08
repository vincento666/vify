import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function waitForPanelSettled(page) {
  await page.evaluate(() => new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve))
  }))
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'load' })
  await page.getByRole('button', { name: '添加节点', exact: true }).click()
  await page.getByTestId('bottom-node-palette').getByRole('button', { name: '大模型', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByTestId('llm-model-section').waitFor({ state: 'visible', timeout: 5000 })
  await waitForPanelSettled(page)
  await panel.getByTestId('llm-model-display').click({ force: true })
  const picker = panel.getByTestId('llm-model-selector')
  await picker.waitFor({ state: 'visible', timeout: 5000 })

  const search = picker.getByPlaceholder('搜索模型名称、供应商或能力')
  await search.fill('gpt')
  await picker.getByRole('button', { name: '搜索模型', exact: true }).click()

  const text = await picker.innerText()
  assert(text.includes('gpt-4.1-mini'), `Filtered model list should include gpt option, got ${text}`)
  assert(!text.includes('xiaomi/mimo-v2-flash'), `Filtered model list should hide non-matching models, got ${text}`)

  await search.fill('mimo')
  await picker.getByRole('button', { name: '搜索模型', exact: true }).click()
  const filteredText = await picker.innerText()
  assert(filteredText.includes('xiaomi/mimo-v2-flash'), `Filtered model list should include mimo option, got ${filteredText}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow model selector search 028')
} finally {
  await browser.close()
}
