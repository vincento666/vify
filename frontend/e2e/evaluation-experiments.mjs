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

async function unwrapResponse(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function selectOnlyEvaluator(page, evaluatorName) {
  const rows = page.locator('.evaluator-selection-row')
  const count = await rows.count()
  for (let index = 0; index < count; index += 1) {
    const row = rows.nth(index)
    const checkbox = row.locator('input[type="checkbox"]')
    const isTarget = (await row.innerText()).includes(evaluatorName)
    await checkbox.setChecked(isTarget)
  }
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
  await page.getByTestId('experiment-step-next').click()
  await page.getByTestId('experiment-eval-set').selectOption({ label: `${evalSetName}（1 条用例）` })
  await page.getByTestId('experiment-step-next').click()
  await page.getByTestId('experiment-target-type').selectOption('AGENT')
  await page.getByTestId('experiment-target').selectOption({ label: agentName })
  await page.getByTestId('experiment-step-next').click()
  await selectOnlyEvaluator(page, evaluatorName)
  await page.getByTestId('experiment-step-next').click()
  await assertBodyIncludes(page, experimentName)
  await assertBodyIncludes(page, 'AGENT')
  const runResponse = page.waitForResponse((response) =>
    response.url().includes('/api/v1/evaluation-experiments/')
      && response.url().endsWith('/runs')
      && response.request().method() === 'POST',
  )
  await page.getByTestId('save-run-experiment').click()
  const run = await unwrapResponse(await runResponse, 'run experiment')

  assert(run.status === 'COMPLETED', `Expected completed run, got ${run.status}`)
  assert(run.passRate === 1, `Expected 100% pass rate, got ${run.passRate}`)
  assert(run.failedCases === 0, `Expected 0 failed cases, got ${run.failedCases}`)
  await page.locator('.experiment-card', { hasText: experimentName }).waitFor({ state: 'visible', timeout: 10000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS evaluation experiments run e2e ${experimentName}`)
} finally {
  await browser.close()
}
