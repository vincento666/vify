import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT
const workbenchScreenshotPath = process.env.HIFY_E2E_WORKBENCH_SCREENSHOT

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
  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `020.7 LLM Workbench Workflow ${stamp}`,
      description: 'llm evaluator workbench target',
      nodes: [
        { nodeKey: 'start', type: 'START', name: 'Start', config: { outputVariables: ['userMessage'] } },
        { nodeKey: 'end', type: 'END', name: 'End', config: { output: '{{start.userMessage}}', outputVariable: 'output' } },
      ],
      edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
    },
  }), 'create workflow')
  const evalSet = await unwrap(await page.request.post(`${baseUrl}/api/v1/eval-sets`, {
    data: { name: `020.7 LLM Workbench Eval Set ${stamp}`, description: 'llm workbench selector' },
  }), 'create eval set')
  await unwrap(await page.request.post(`${baseUrl}/api/v1/eval-sets/${evalSet.id}/cases`, {
    data: { input: 'refund policy', expectedOutput: 'refund policy', tags: ['llm-workbench'] },
  }), 'create case')

  await page.goto(`${baseUrl}/evaluation`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '评估器', exact: true }).click()
  await page.getByTestId('open-llm-evaluator-workbench').click()
  await page.getByTestId('llm-evaluator-workbench').waitFor({ state: 'visible', timeout: 10000 })

  const modelSelect = page.getByTestId('llm-workbench-model')
  const optionCount = await modelSelect.locator('option').count()
  assert(optionCount > 1, 'Expected at least one enabled model option for LLM workbench E2E')
  await modelSelect.selectOption({ index: 1 })
  const evaluatorName = `020.7 LLM Judge ${stamp}`
  await page.getByTestId('llm-workbench-name').fill(evaluatorName)
  await page.getByTestId('llm-workbench-prompt').fill('Pass when actual output preserves the expected answer.')
  await page.getByTestId('llm-workbench-expected').fill('refund policy')
  await page.getByTestId('llm-workbench-actual').fill('refund policy')
  await page.getByTestId('llm-workbench-debug').click()
  await page.getByTestId('llm-debug-result').getByText('通过', { exact: true }).waitFor({ state: 'visible', timeout: 15000 })
  await page.getByTestId('llm-debug-raw').getByText('mock judge', { exact: false }).waitFor({ state: 'visible', timeout: 10000 })
  if (workbenchScreenshotPath) {
    await page.screenshot({ path: workbenchScreenshotPath, fullPage: true })
  }
  await page.getByTestId('llm-workbench-publish').click()
  await page.getByTestId('llm-workbench-published-version').getByText('v0.0.1', { exact: false }).waitFor({ state: 'visible', timeout: 10000 })

  const evaluatorPage = await unwrap(await page.request.get(`${baseUrl}/api/v1/evaluators`, {
    params: { page: 1, pageSize: 20, name: evaluatorName },
  }), 'find llm evaluator')
  const evaluator = evaluatorPage.list.find(item => item.name === evaluatorName)
  assert(evaluator, 'Expected LLM evaluator to exist after workbench publish')

  await page.getByRole('tab', { name: '实验', exact: true }).click()
  await page.getByTestId('create-experiment').click()
  await page.getByTestId('experiment-name').fill(`020.7 LLM Experiment ${stamp}`)
  await page.getByTestId('experiment-step-next').click()
  await page.getByTestId('experiment-eval-set').selectOption(String(evalSet.id))
  await page.getByTestId('experiment-step-next').click()
  await page.getByTestId('experiment-target-type').selectOption('WORKFLOW')
  await page.getByTestId('experiment-target').selectOption(String(workflow.id))
  await page.getByTestId('experiment-step-next').click()
  const evaluatorCheckbox = page.getByTestId(`evaluator-checkbox-${evaluator.id}`)
  if (!(await evaluatorCheckbox.isChecked())) {
    await evaluatorCheckbox.check()
  }
  await page.getByTestId(`evaluator-version-${evaluator.id}`).selectOption({ label: 'v0.0.1' })
  await page.getByTestId('experiment-step-next').click()
  await page.getByText('评估器版本：v0.0.1', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS llm evaluator workbench e2e evaluator=${evaluator.id}`)
} finally {
  await browser.close()
}
