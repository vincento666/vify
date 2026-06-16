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

function flowPayload(name) {
  return {
    name,
    description: 'mapping workflow target',
    nodes: [
      { nodeKey: 'start', type: 'START', name: 'Start', config: { outputVariables: ['userMessage'] } },
      { nodeKey: 'end', type: 'END', name: 'End', config: { output: '{{start.userMessage}}', outputVariable: 'output' } },
    ],
    edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
  }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  const stamp = Date.now()
  const evalSetName = `020.5 Mapping Set ${stamp}`
  const workflowName = `020.5 Mapping Workflow ${stamp}`
  const evaluatorName = `020.5 Exact ${stamp}`
  const experimentName = `020.5 Mapping Experiment ${stamp}`

  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: flowPayload(workflowName),
  }), 'create workflow')
  const evalSet = await unwrap(await page.request.post(`${baseUrl}/api/v1/eval-sets`, {
    data: { name: evalSetName, description: 'mapping e2e' },
  }), 'create eval set')
  await unwrap(await page.request.put(`${baseUrl}/api/v1/eval-sets/${evalSet.id}/fields`, {
    data: {
      fields: [
        { key: 'input', label: 'Input', contentType: 'TEXT', required: true, displayOrder: 1 },
        { key: 'expectedOutput', label: 'Expected', contentType: 'TEXT', required: true, displayOrder: 2 },
        { key: 'prompt', label: 'Prompt', contentType: 'TEXT', required: true, displayOrder: 3 },
        { key: 'reference', label: 'Reference', contentType: 'TEXT', required: true, displayOrder: 4 },
      ],
    },
  }), 'update fields')
  await unwrap(await page.request.post(`${baseUrl}/api/v1/eval-sets/${evalSet.id}/cases`, {
    data: {
      input: 'wrong input',
      expectedOutput: 'wrong expected',
      tags: ['mapping'],
      metadata: { prompt: 'mapped browser prompt', reference: 'mapped browser prompt' },
    },
  }), 'create case')
  await unwrap(await page.request.post(`${baseUrl}/api/v1/evaluators`, {
    data: { name: evaluatorName, type: 'EXACT_MATCH', config: {} },
  }), 'create evaluator')

  await page.goto(`${baseUrl}/evaluation`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '实验', exact: true }).click()
  await page.getByTestId('create-experiment').click()
  await page.getByTestId('experiment-name').fill(experimentName)
  await page.getByTestId('experiment-item-concurrency').fill('3')
  await page.getByTestId('experiment-item-retry-count').fill('2')
  await page.getByTestId('experiment-step-next').click()
  await page.getByTestId('experiment-eval-set').selectOption({ label: `${evalSetName}（1 条用例）` })
  await page.getByTestId('experiment-step-next').click()
  await page.getByTestId('experiment-target-type').selectOption('WORKFLOW')
  await page.getByTestId('experiment-target').selectOption({ label: workflowName })
  await page.getByTestId('target-user-message-field').selectOption('prompt')
  await page.getByTestId('experiment-step-next').click()
  await page.locator('label', { hasText: evaluatorName }).locator('input[type="checkbox"]').setChecked(true)
  await page.getByTestId('evaluator-expected-output-field').selectOption('reference')
  await page.getByTestId('experiment-step-next').click()
  await page.getByText('目标输入：prompt', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText('期望字段：reference', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByText('并发：3', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await page.getByTestId('save-run-experiment').click()
  await page.getByText(experimentName, { exact: true }).waitFor({ state: 'visible', timeout: 15000 })
  await page.getByText('COMPLETED', { exact: true }).waitFor({ state: 'visible', timeout: 15000 })
  await page.getByText('100.0%', { exact: true }).waitFor({ state: 'visible', timeout: 15000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS experiment mapping settings e2e evalSet=${evalSet.id}`)
} finally {
  await browser.close()
}
