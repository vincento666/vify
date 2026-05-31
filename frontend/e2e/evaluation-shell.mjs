import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

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
  await assertBodyIncludes(page, '评测')
  await assertBodyIncludes(page, 'Experiments')
  await assertBodyIncludes(page, 'Eval Sets')
  await assertBodyIncludes(page, 'Evaluators')
  await assertBodyIncludes(page, 'Run Records')
  await assertBodyIncludes(page, 'Compare Analysis')
  await assertBodyIncludes(page, '先跑一次 Agent 实验')

  const compareTab = page.getByRole('tab', { name: 'Compare Analysis' })
  await compareTab.waitFor({ state: 'visible', timeout: 5000 })
  const compareClass = await compareTab.getAttribute('class')
  assert(compareClass?.includes('is-disabled'), 'Expected Compare Analysis tab to be disabled in MVP')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  await page.getByRole('tab', { name: 'Eval Sets' }).click()
  await assertBodyIncludes(page, '整理回归用例')

  await page.getByRole('tab', { name: 'Evaluators' }).click()
  await assertBodyIncludes(page, '定义可解释评分规则')

  await page.getByRole('tab', { name: 'Run Records' }).click()
  await assertBodyIncludes(page, '暂无运行记录')

  console.log('PASS evaluation workbench shell e2e')
} finally {
  await browser.close()
}
