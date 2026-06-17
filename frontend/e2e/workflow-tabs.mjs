import { chromium } from 'playwright'
import { resolveFrontendServer } from './support/dev-server.mjs'

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

const server = await resolveFrontendServer()
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${server.baseUrl}/workflows`, { waitUntil: 'networkidle' })
  await assertBodyIncludes(page, '工作流')
  await assertBodyIncludes(page, '对话流')
  await assertBodyIncludes(page, '新建工作流')
  await assertBodyIncludes(page, '管理智能客服分类等工作流配置')

  await page.getByRole('tab', { name: '对话流' }).click()
  await page.waitForURL('**/chatflows')
  await assertBodyIncludes(page, '新建对话流')
  await assertBodyIncludes(page, '管理面向对话场景的流程编排')

  await page.getByRole('tab', { name: '工作流' }).click()
  await page.waitForURL('**/workflows')
  await page.getByRole('button', { name: '新建工作流' }).click()
  await page.waitForURL('**/workflows/create')
  await assertBodyIncludes(page, '画布概览')
  await assertBodyIncludes(page, '编排')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow/chatflow tab shell e2e')
} finally {
  await browser.close()
  await server.close()
}
