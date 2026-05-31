import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const targetOutput = process.env.HIFY_E2E_TARGET_OUTPUT || 'LLM mock: refund only'

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function assertBodyIncludes(page, text) {
  const body = await page.locator('body').innerText()
  assert(body.includes(text), `Expected page body to include: ${text}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/evaluation`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: 'Run Records' }).click()
  await assertBodyIncludes(page, 'Run #')

  await page.getByRole('button', { name: '查看报告' }).first().click()
  await page.getByText(targetOutput).waitFor({ state: 'visible', timeout: 10000 })
  await assertBodyIncludes(page, 'failed cases need investigation')
  await assertBodyIncludes(page, 'FAILED')
  await assertBodyIncludes(page, targetOutput)
  await assertBodyIncludes(page, 'policy')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS evaluation run records report e2e')
} finally {
  await browser.close()
}
