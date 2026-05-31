import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

async function assertBodyIncludes(page, text) {
  const body = await page.locator('body').innerText()
  assert(body.includes(text), `Expected page body to include: ${text}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/workflows`, { waitUntil: 'networkidle' })
  await assertBodyIncludes(page, 'Workflow')
  await assertBodyIncludes(page, 'Chatflow')
  await assertBodyIncludes(page, '新建工作流')
  await assertBodyIncludes(page, '工作流名称')

  await page.getByRole('tab', { name: 'Chatflow' }).click()
  await page.waitForURL('**/chatflows')
  await assertBodyIncludes(page, '新建 Chatflow')
  await assertBodyIncludes(page, 'Chatflow 资源入口已就绪')

  await page.getByRole('tab', { name: 'Workflow' }).click()
  await page.waitForURL('**/workflows')
  await page.getByRole('button', { name: '新建工作流' }).click()
  await page.waitForURL('**/workflows/create')
  await assertBodyIncludes(page, '画布 Builder 入口已就绪')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow/chatflow tab shell e2e')
} finally {
  await browser.close()
}
