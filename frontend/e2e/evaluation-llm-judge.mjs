import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const providerName = process.env.HIFY_E2E_PROVIDER_NAME
const modelName = process.env.HIFY_E2E_MODEL_NAME || 'LLM Judge E2E Model'
const evaluatorName = `E2E LLM Judge ${Date.now()}`

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function assertBodyIncludes(page, text) {
  const body = await page.locator('body').innerText()
  assert(body.includes(text), `Expected page body to include: ${text}`)
}

if (!providerName) {
  throw new Error('Missing HIFY_E2E_PROVIDER_NAME')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/evaluation`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: 'Evaluators' }).click()
  await page.getByTestId('create-evaluator').click()
  await page.getByPlaceholder('请输入评估器名称').fill(evaluatorName)
  await page.locator('.el-segmented__item-label', { hasText: 'LLM Judge' }).click()
  await page.getByTestId('llm-judge-model').selectOption({ label: `${providerName} / ${modelName}` })
  await page.getByPlaceholder('Exact Match 会使用该字段').fill('refund policy')
  await page.getByPlaceholder('粘贴一次 Agent 回复用于试跑').fill('refund policy')
  await page.getByTestId('test-evaluator-sample').click()
  await page.getByText('PASS').waitFor({ state: 'visible', timeout: 10000 })
  await assertBodyIncludes(page, 'mock judge')

  await page.getByTestId('save-evaluator').click()
  await page.locator('.el-dialog', { hasText: '创建评估器' }).waitFor({ state: 'hidden', timeout: 5000 })
  await page.locator('h4', { hasText: evaluatorName }).waitFor({ state: 'visible', timeout: 5000 })
  await assertBodyIncludes(page, 'LLM Judge')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS evaluation LLM judge e2e ${evaluatorName}`)
} finally {
  await browser.close()
}
