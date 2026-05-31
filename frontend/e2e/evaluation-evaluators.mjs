import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const timestamp = Date.now()
const evaluatorName = `E2E Keyword Evaluator ${timestamp}`

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
  await page.getByRole('tab', { name: 'Evaluators' }).click()
  await assertBodyIncludes(page, '创建评估器')

  await page.getByTestId('create-evaluator').click()
  await page.getByPlaceholder('请输入评估器名称').fill(evaluatorName)
  await page.getByPlaceholder('用英文逗号分隔，如 refund,policy').fill('refund, policy, refund')
  await page.getByPlaceholder('粘贴一次 Agent 回复用于试跑').fill('Refund policy is available within seven days.')
  await page.getByTestId('test-evaluator-sample').click()
  await page.getByText('PASS').waitFor({ state: 'visible', timeout: 5000 })
  await assertBodyIncludes(page, 'Score 1')

  await page.getByTestId('save-evaluator').click()
  await page.locator('.el-dialog', { hasText: '创建评估器' }).waitFor({ state: 'hidden', timeout: 5000 })
  await page.locator('h4', { hasText: evaluatorName }).waitFor({ state: 'visible', timeout: 5000 })
  await assertBodyIncludes(page, 'Contains Keywords')
  await assertBodyIncludes(page, 'refund, policy')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS evaluation evaluators e2e ${evaluatorName}`)
} finally {
  await browser.close()
}
