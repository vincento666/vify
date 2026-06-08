import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function nodeCount(page, id) {
  return page.locator(`.vue-flow__node[data-id="${id}"]`).count()
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'networkidle' })
  const start = page.locator('.vue-flow__node[data-id="start"]')
  const end = page.locator('.vue-flow__node[data-id="end"]')
  await start.waitFor({ state: 'visible', timeout: 5000 })
  await end.waitFor({ state: 'visible', timeout: 5000 })

  await start.click()
  await page.keyboard.press('Backspace')
  await page.keyboard.press('Delete')
  await page.keyboard.press('Enter')
  assert(await nodeCount(page, 'start') === 1, 'START node must survive keyboard delete keys')

  await page.getByRole('button', { name: '关闭配置', exact: true }).click()
  await end.click()
  await page.keyboard.press('Backspace')
  await page.keyboard.press('Delete')
  await page.keyboard.press('Enter')
  assert(await nodeCount(page, 'end') === 1, 'END node must survive keyboard delete keys')

  const toolbar = page.getByTestId('canvas-bottom-toolbar')
  await toolbar.getByRole('button', { name: '添加节点', exact: true }).click()
  await page.getByRole('button', { name: '大模型', exact: true }).click()
  assert(await nodeCount(page, 'start') === 1, 'START node must not be recreated as a side effect')
  assert(await nodeCount(page, 'end') === 1, 'END node must not be recreated as a side effect')

  const startText = await start.innerText()
  const endText = await end.innerText()
  assert(startText.includes('输出'), `START card should expose output variables, got ${startText}`)
  assert(!startText.includes('输入'), `START card should not label its variables as input, got ${startText}`)
  assert(endText.includes('输入'), `END card should expose input variables, got ${endText}`)
  assert(!endText.includes('输出'), `END card should not show output row on the canvas card, got ${endText}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow fixed node deletion e2e')
} finally {
  await browser.close()
}
