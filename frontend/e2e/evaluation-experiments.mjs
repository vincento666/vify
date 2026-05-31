import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const agentName = process.env.HIFY_E2E_AGENT_NAME
const evalSetName = process.env.HIFY_E2E_EVAL_SET_NAME
const evaluatorName = process.env.HIFY_E2E_EVALUATOR_NAME
const experimentName = process.env.HIFY_E2E_EXPERIMENT_NAME || `E2E Agent Experiment ${Date.now()}`

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function assertBodyIncludes(page, text) {
  const body = await page.locator('body').innerText()
  assert(body.includes(text), `Expected page body to include: ${text}`)
}

if (!agentName || !evalSetName || !evaluatorName) {
  throw new Error('Missing HIFY_E2E_AGENT_NAME, HIFY_E2E_EVAL_SET_NAME, or HIFY_E2E_EVALUATOR_NAME')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/evaluation`, { waitUntil: 'networkidle' })
  await assertBodyIncludes(page, '创建实验')

  await page.getByTestId('create-experiment').click()
  await page.getByTestId('experiment-name').fill(experimentName)
  await page.getByTestId('experiment-target-type').selectOption('AGENT')
  await page.getByTestId('experiment-target').selectOption({ label: agentName })
  await page.getByTestId('experiment-eval-set').selectOption({ label: `${evalSetName} (1 cases)` })
  await page.locator('label', { hasText: evaluatorName }).locator('input[type="checkbox"]').check()
  await page.getByTestId('save-run-experiment').click()

  await page.locator('.el-dialog', { hasText: '创建实验' }).waitFor({ state: 'hidden', timeout: 10000 })
  await assertBodyIncludes(page, experimentName)
  await assertBodyIncludes(page, '最新运行结果')
  await assertBodyIncludes(page, 'COMPLETED')
  await assertBodyIncludes(page, '100.0%')
  await assertBodyIncludes(page, '0 failed')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS evaluation experiments run e2e ${experimentName}`)
} finally {
  await browser.close()
}
