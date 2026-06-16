import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const suffix = Date.now()
const targetOutput = 'LLM mock: Workflow says refund only'

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function assertBodyIncludes(page, text) {
  const body = await page.locator('body').innerText()
  assert(body.includes(text), `Expected page body to include: ${text}`)
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

async function seedFailedReportRun() {
  const workflow = await api('/workflows', {
    method: 'POST',
    body: JSON.stringify({
      name: `E2E Report Workflow ${suffix}`,
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
    body: JSON.stringify({ name: `E2E Report Set ${suffix}`, description: 'run records report e2e' }),
  })
  await api(`/eval-sets/${evalSet.id}/cases`, {
    method: 'POST',
    body: JSON.stringify({ input: 'refund only', expectedOutput: 'refund policy', tags: ['report'] }),
  })
  const evaluator = await api('/evaluators', {
    method: 'POST',
    body: JSON.stringify({
      name: `E2E Report Keywords ${suffix}`,
      type: 'CONTAINS_KEYWORDS',
      config: { keywords: ['policy'], matchMode: 'all', ignoreCase: true },
    }),
  })
  const experiment = await api('/evaluation-experiments', {
    method: 'POST',
    body: JSON.stringify({
      name: `E2E Report Experiment ${suffix}`,
      targetType: 'WORKFLOW',
      targetId: workflow.id,
      evalSetId: evalSet.id,
      evaluatorIds: [evaluator.id],
    }),
  })
  const run = await api(`/evaluation-experiments/${experiment.id}/runs`, { method: 'POST', body: '{}' })
  assert(run.failedCases === 1, 'Seeded report run should fail one case')
  return { experiment, run, workflow }
}

const seeded = await seedFailedReportRun()
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/evaluation`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '运行记录', exact: true }).click()

  const runCard = page.locator('.run-card').filter({
    has: page.locator('p').filter({ hasText: new RegExp(`^实验 #${seeded.experiment.id}$`) }),
  })
  await runCard.waitFor({ state: 'visible', timeout: 10000 })
  assert(await runCard.count() === 1, `Expected one run card for experiment ${seeded.experiment.id}`)
  await runCard.getByRole('button', { name: '查看报告' }).click()
  await page.getByText(targetOutput).waitFor({ state: 'visible', timeout: 10000 })
  await assertBodyIncludes(page, '个失败用例需要排查')
  await assertBodyIncludes(page, 'FAILED')
  await assertBodyIncludes(page, targetOutput)
  await assertBodyIncludes(page, 'policy')
  const debugLink = page.getByTestId('target-debug-link').filter({ hasText: '查看 Workflow 调试' }).first()
  await debugLink.waitFor({ state: 'visible', timeout: 10000 })
  const href = await debugLink.getAttribute('href')
  assert(
    href?.startsWith(`/workflows/${seeded.workflow.id}/canvas?runId=`) && href.endsWith('&debug=1'),
    `Expected Workflow debug link, got ${href}`,
  )

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  await debugLink.click()
  await page.waitForFunction((workflowId) => {
    const params = new URLSearchParams(window.location.search)
    return window.location.pathname === `/workflows/${workflowId}/canvas`
      && Boolean(params.get('runId'))
      && params.get('debug') === '1'
  }, seeded.workflow.id, { timeout: 10000 })

  console.log('PASS evaluation run records report e2e')
} finally {
  await browser.close()
}
