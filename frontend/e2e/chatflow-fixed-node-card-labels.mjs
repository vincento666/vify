import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/chatflows/create`, { waitUntil: 'load' })
  await page.locator('.vue-flow__node[data-id="start"]').waitFor({ state: 'visible', timeout: 5000 })
  await page.locator('.vue-flow__node[data-id="end"]').waitFor({ state: 'visible', timeout: 5000 })

  const startText = await page.locator('.vue-flow__node[data-id="start"]').innerText()
  const endText = await page.locator('.vue-flow__node[data-id="end"]').innerText()

  assert(startText.includes('开始'), `Expected START card title, got ${startText}`)
  assert(startText.includes('输出'), `START card must label its configured variables as 输出, got ${startText}`)
  assert(!startText.includes('输入'), `START card must not label its configured variables as 输入, got ${startText}`)
  assert(startText.includes('USER_INPUT'), `START card should show USER_INPUT, got ${startText}`)

  assert(endText.includes('结束'), `Expected END card title, got ${endText}`)
  assert(endText.includes('输入'), `END card must label its return variables as 输入, got ${endText}`)
  assert(!endText.includes('输出'), `END card must not label its return variables as 输出, got ${endText}`)
  assert(endText.includes('output'), `END card should show output, got ${endText}`)

  console.log('PASS chatflow fixed node card labels')
} finally {
  await browser.close()
}
