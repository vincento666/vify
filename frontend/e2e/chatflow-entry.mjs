import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function assertBodyIncludes(page, text) {
  const body = await page.locator('body').innerText()
  assert(body.includes(text), `Expected page to include: ${text}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/workflows`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: 'Chatflow' }).click()
  await page.waitForURL('**/chatflows')
  await assertBodyIncludes(page, '新建 Chatflow')
  await assertBodyIncludes(page, 'Chatflow 资源入口已就绪')

  await page.getByRole('button', { name: '新建 Chatflow' }).click()
  await page.waitForURL('**/chatflows/create')
  await assertBodyIncludes(page, '新建 Chatflow')
  await assertBodyIncludes(page, 'START')
  await assertBodyIncludes(page, 'END')

  await page.goto(`${baseUrl}/chatflows/42/canvas`, { waitUntil: 'networkidle' })
  await assertBodyIncludes(page, 'Chatflow #42')
  await assertBodyIncludes(page, '对话流程画布入口')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow resource entry e2e')
} finally {
  await browser.close()
}
