import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  const stamp = Date.now()
  const evaluator = await unwrap(await page.request.post(`${baseUrl}/api/v1/evaluators`, {
    data: {
      name: `020.6 Versioned Evaluator ${stamp}`,
      type: 'CONTAINS_KEYWORDS',
      config: { keywords: ['refund'], matchMode: 'all', ignoreCase: true },
    },
  }), 'create evaluator')
  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `020.6 Version Workflow ${stamp}`,
      description: 'evaluator version selector target',
      nodes: [
        { nodeKey: 'start', type: 'START', name: 'Start', config: { outputVariables: ['userMessage'] } },
        { nodeKey: 'end', type: 'END', name: 'End', config: { output: '{{start.userMessage}}', outputVariable: 'output' } },
      ],
      edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
    },
  }), 'create workflow')
  const evalSet = await unwrap(await page.request.post(`${baseUrl}/api/v1/eval-sets`, {
    data: { name: `020.6 Version Eval Set ${stamp}`, description: 'evaluator version selector' },
  }), 'create eval set')
  await unwrap(await page.request.post(`${baseUrl}/api/v1/eval-sets/${evalSet.id}/cases`, {
    data: { input: 'refund policy', expectedOutput: 'refund policy', tags: ['version'] },
  }), 'create case')

  await page.goto(`${baseUrl}/evaluation`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '评估器', exact: true }).click()
  await page.getByTestId('evaluator-custom-tab').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('evaluator-preset-tab').click()
  await page.getByText('精确匹配', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText('代码评估器', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText('禁用', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('evaluator-custom-tab').click()
  await page.getByText(evaluator.name, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId(`publish-evaluator-version-${evaluator.id}`).click()
  await page.locator('article', { hasText: evaluator.name }).getByText('v0.0.1', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('tab', { name: '实验', exact: true }).click()
  await page.getByTestId('create-experiment').click()
  await page.getByTestId('experiment-name').fill(`020.6 Version Experiment ${stamp}`)
  await page.getByTestId('experiment-step-next').click()
  await page.getByTestId('experiment-eval-set').selectOption(String(evalSet.id))
  await page.getByTestId('experiment-step-next').click()
  await page.getByTestId('experiment-target-type').selectOption('WORKFLOW')
  await page.getByTestId('experiment-target').selectOption(String(workflow.id))
  await page.getByTestId('experiment-step-next').click()
  await page.getByText(evaluator.name, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  const evaluatorCheckbox = page.getByTestId(`evaluator-checkbox-${evaluator.id}`)
  if (!(await evaluatorCheckbox.isChecked())) {
    await evaluatorCheckbox.check()
  }
  await page.getByTestId(`evaluator-version-${evaluator.id}`).selectOption({ label: 'v0.0.1' })
  await page.getByTestId('experiment-step-next').click()
  await page.getByText('评估器版本：v0.0.1', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('save-run-experiment').click()
  await page.getByText('最新运行结果', { exact: true }).waitFor({ state: 'visible', timeout: 15000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS evaluator versions presets e2e evaluator=${evaluator.id}`)
} finally {
  await browser.close()
}
