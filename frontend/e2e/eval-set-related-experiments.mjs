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
    description: 'related experiment workflow target',
    nodes: [
      { nodeKey: 'start', type: 'START', name: 'Start', config: { outputVariables: ['userMessage'] } },
      { nodeKey: 'end', type: 'END', name: 'End', config: { output: '{{start.userMessage}}', outputVariable: 'output' } },
    ],
    edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
  }
}

async function openEvalSet(page, name) {
  await page.goto(`${baseUrl}/evaluation?tab=eval-sets`, { waitUntil: 'networkidle' })
  await page.getByText(name, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  const card = page.locator('.eval-set-card').filter({ hasText: name })
  await card.getByTestId('view-eval-set-detail').click()
  await page.getByTestId('eval-set-related-tab').click()
  await page.getByTestId('related-experiments-panel').waitFor({ state: 'visible', timeout: 10000 })
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  const stamp = Date.now()
  const setName = `020.3 Related Set ${stamp}`
  const experimentName = `020.3 Related Experiment ${stamp}`
  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: flowPayload(`020.3 Related Workflow ${stamp}`),
  }), 'create workflow')
  const evalSet = await unwrap(await page.request.post(`${baseUrl}/api/v1/eval-sets`, {
    data: { name: setName, description: 'related e2e' },
  }), 'create eval set')
  await unwrap(await page.request.post(`${baseUrl}/api/v1/eval-sets/${evalSet.id}/cases`, {
    data: { input: 'hello', expectedOutput: 'hello', tags: ['related'], metadata: {} },
  }), 'create eval case')
  const version = await unwrap(await page.request.post(`${baseUrl}/api/v1/eval-sets/${evalSet.id}/versions`, {
    data: { description: 'related version' },
  }), 'submit version')
  const evaluator = await unwrap(await page.request.post(`${baseUrl}/api/v1/evaluators`, {
    data: { name: `020.3 Exact ${stamp}`, type: 'EXACT_MATCH', config: {} },
  }), 'create evaluator')
  const experiment = await unwrap(await page.request.post(`${baseUrl}/api/v1/evaluation-experiments`, {
    data: {
      name: experimentName,
      targetType: 'WORKFLOW',
      targetId: workflow.id,
      evalSetId: evalSet.id,
      evalSetVersionId: version.id,
      evaluatorIds: [evaluator.id],
    },
  }), 'create experiment')

  await openEvalSet(page, setName)
  const panel = page.getByTestId('related-experiments-panel')
  await panel.getByText(experimentName, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByText('v0.0.1', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByText('WORKFLOW', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByText('READY', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })

  const related = await unwrap(await page.request.get(`${baseUrl}/api/v1/eval-sets/${evalSet.id}/related-experiments`), 'related api')
  assert(related.total === 1, `Expected one related experiment, got ${related.total}`)
  assert(related.list[0].id === experiment.id, 'Expected related experiment id to match created experiment')
  assert(related.list[0].evalSetVersionId === version.id, 'Expected related version id to match submitted version')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS eval set related experiments e2e evalSet=${evalSet.id} experiment=${experiment.id}`)
} finally {
  await browser.close()
}
