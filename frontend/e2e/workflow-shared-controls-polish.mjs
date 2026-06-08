import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function computed(page, selector) {
  return page.locator(selector).first().evaluate((element) => {
    const style = getComputedStyle(element)
    return {
      border: style.borderColor,
      background: style.backgroundColor,
      width: style.width,
      height: style.height,
      text: element.textContent?.trim() || '',
      svg: element.querySelectorAll('svg').length,
    }
  })
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="end"]').click()
  await page.getByTestId('node-config-panel').waitFor({ state: 'visible', timeout: 5000 })

  const closeButton = await computed(page, '[aria-label="关闭配置"]')
  assert(closeButton.svg >= 1, `Close action must use lightweight icon, got ${JSON.stringify(closeButton)}`)
  assert(!closeButton.text.includes('×'), `Close action must not render raw x text, got ${JSON.stringify(closeButton)}`)
  assert(closeButton.border !== 'rgba(0, 0, 0, 0)' && closeButton.background !== 'rgba(0, 0, 0, 0)', `Icon button must have visible border/background ${JSON.stringify(closeButton)}`)

  await page.getByRole('button', { name: '添加节点', exact: true }).click()
  const addButton = await computed(page, '[aria-label="添加节点"]')
  assert(addButton.svg >= 1, `Add node button must keep icon ${JSON.stringify(addButton)}`)

  await page.getByTestId('bottom-node-palette').getByRole('button', { name: '大模型', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()
  const modelSettings = await computed(page, '[aria-label="模型设置"]')
  assert(modelSettings.svg >= 1, `Model settings must use icon ${JSON.stringify(modelSettings)}`)
  assert(modelSettings.border !== 'rgba(0, 0, 0, 0)' && modelSettings.background !== 'rgba(0, 0, 0, 0)', `Model settings must have visible surface ${JSON.stringify(modelSettings)}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log('PASS workflow shared controls polish')
} finally {
  await browser.close()
}
