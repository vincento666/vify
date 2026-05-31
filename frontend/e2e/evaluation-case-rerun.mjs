import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const suffix = Date.now()

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function api(path, options = {}) {
  const response = await fetch(`${baseUrl}/api/v1${path}`, {
    headers: { 'content-type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  const json = await response.json()
  if (!response.ok || json.code !== 200) {
    throw new Error(`API ${path} failed: ${response.status} ${JSON.stringify(json)}`)
  }
  return json.data
}

async function seedFailedRunThenRelaxEvaluator() {
  const workflow = await api('/workflows', {
    method: 'POST',
    body: JSON.stringify({
      name: `E2E Rerun Workflow ${suffix}`,
      description: '',
      nodes: [
        { nodeKey: 'start', type: 'START', name: 'Start', config: { outputVariables: ['userMessage'] } },
        {
          nodeKey: 'llm',
          type: 'LLM',
          name: 'LLM',
          config: { prompt: 'Workflow says {{start.userMessage}}', outputVariable: 'answer' },
        },
        { nodeKey: 'end', type: 'END', name: 'End', config: { output: '{{llm.answer}}', outputVariable: 'output' } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'llm', condition: null },
        { sourceNodeKey: 'llm', targetNodeKey: 'end', condition: null },
      ],
    }),
  })
  const evalSet = await api('/eval-sets', {
    method: 'POST',
    body: JSON.stringify({ name: `E2E Rerun Set ${suffix}`, description: 'selected rerun e2e' }),
  })
  await api(`/eval-sets/${evalSet.id}/cases`, {
    method: 'POST',
    body: JSON.stringify({ input: 'refund only', expectedOutput: 'refund policy', tags: ['rerun'] }),
  })
  const evaluator = await api('/evaluators', {
    method: 'POST',
    body: JSON.stringify({
      name: `E2E Rerun Keywords ${suffix}`,
      type: 'CONTAINS_KEYWORDS',
      config: { keywords: ['policy'], matchMode: 'all', ignoreCase: true },
    }),
  })
  const experiment = await api('/evaluation-experiments', {
    method: 'POST',
    body: JSON.stringify({
      name: `E2E Rerun Experiment ${suffix}`,
      targetType: 'WORKFLOW',
      targetId: workflow.id,
      evalSetId: evalSet.id,
      evaluatorIds: [evaluator.id],
    }),
  })
  const run = await api(`/evaluation-experiments/${experiment.id}/runs`, { method: 'POST', body: '{}' })
  assert(run.failedCases === 1, 'Seeded run should fail before rerun')
  await api(`/evaluators/${evaluator.id}`, {
    method: 'PUT',
    body: JSON.stringify({
      name: evaluator.name,
      type: 'CONTAINS_KEYWORDS',
      config: { keywords: ['refund'], matchMode: 'all', ignoreCase: true },
    }),
  })
  return { experiment, run }
}

const seeded = await seedFailedRunThenRelaxEvaluator()
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/evaluation`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: 'Run Records' }).click()
  const runCard = page.locator('.run-card', { hasText: `Experiment #${seeded.experiment.id}` })
  await runCard.getByRole('button', { name: '查看报告' }).click()

  const report = page.locator('.report-panel')
  await report.locator('.summary-metrics').getByText('1 failed', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await report.getByText('Workflow says refund only').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('rerun-case-result').click()
  await page.waitForFunction(() => document.querySelector('.report-panel')?.textContent?.includes('0 failed'), null, {
    timeout: 10000,
  })
  const reportText = await report.innerText()
  assert(reportText.includes('Pass 100.0%'), 'Expected rerun report to show 100% pass rate')
  assert(reportText.includes('PASSED'), 'Expected rerun case status to be PASSED')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS evaluation selected case rerun e2e')
} finally {
  await browser.close()
}
