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

function flowPayload(name, prefix) {
  return {
    name,
    description: '',
    nodes: [
      {
        nodeKey: 'start',
        type: 'START',
        name: 'Start',
        config: { outputVariables: ['userMessage'] },
      },
      {
        nodeKey: 'llm',
        type: 'LLM',
        name: 'LLM',
        config: {
          prompt: `${prefix} says {{start.userMessage}}`,
          outputVariable: 'answer',
        },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: 'End',
        config: { output: '{{llm.answer}}', outputVariable: 'output' },
      },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'llm', condition: null },
      { sourceNodeKey: 'llm', targetNodeKey: 'end', condition: null },
    ],
  }
}

async function seed() {
  const workflowName = `E2E Eval Workflow ${suffix}`
  const chatflowName = `E2E Eval Chatflow ${suffix}`
  const evalSetName = `E2E Flow Eval Set ${suffix}`
  const evaluatorName = `E2E Flow Keyword ${suffix}`

  const [workflow, chatflow, evalSet, evaluator] = await Promise.all([
    api('/workflows', { method: 'POST', body: JSON.stringify(flowPayload(workflowName, 'Workflow')) }),
    api('/chatflows', { method: 'POST', body: JSON.stringify(flowPayload(chatflowName, 'Chatflow')) }),
    api('/eval-sets', { method: 'POST', body: JSON.stringify({ name: evalSetName, description: 'flow target e2e' }) }),
    api('/evaluators', {
      method: 'POST',
      body: JSON.stringify({
        name: evaluatorName,
        type: 'CONTAINS_KEYWORDS',
        config: { keywords: ['says warranty'], matchMode: 'all', ignoreCase: true },
      }),
    }),
  ])
  await api(`/eval-sets/${evalSet.id}/cases`, {
    method: 'POST',
    body: JSON.stringify({ input: 'warranty', expectedOutput: 'says warranty', tags: ['flow'] }),
  })
  return { workflow, chatflow, evalSet, evaluator, workflowName, chatflowName, evalSetName, evaluatorName }
}

async function assertBodyIncludes(page, text) {
  const body = await page.locator('body').innerText()
  assert(body.includes(text), `Expected page body to include: ${text}`)
}

async function createAndRunExperiment(page, targetType, targetName, evalSetName, evaluatorName, experimentName) {
  await page.getByTestId('create-experiment').click()
  await page.getByTestId('experiment-name').fill(experimentName)
  await page.getByTestId('experiment-target-type').selectOption(targetType)
  await page.getByTestId('experiment-target').selectOption({ label: targetName })
  await page.getByTestId('experiment-eval-set').selectOption({ label: `${evalSetName} (1 cases)` })
  await page.locator('label', { hasText: evaluatorName }).locator('input[type="checkbox"]').setChecked(true)
  await page.getByTestId('save-run-experiment').click()
  await page.locator('.el-dialog', { hasText: '创建实验' }).waitFor({ state: 'hidden', timeout: 10000 })
  await assertBodyIncludes(page, experimentName)
  await assertBodyIncludes(page, 'COMPLETED')
  await assertBodyIncludes(page, '100.0%')
  await assertBodyIncludes(page, '0 failed')
}

const data = await seed()
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/evaluation`, { waitUntil: 'networkidle' })
  await assertBodyIncludes(page, 'Workflow')
  await assertBodyIncludes(page, 'Chatflow')

  await createAndRunExperiment(
    page,
    'WORKFLOW',
    data.workflowName,
    data.evalSetName,
    data.evaluatorName,
    `E2E Workflow Experiment ${suffix}`,
  )
  await createAndRunExperiment(
    page,
    'CHATFLOW',
    data.chatflowName,
    data.evalSetName,
    data.evaluatorName,
    `E2E Chatflow Experiment ${suffix}`,
  )

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS evaluation workflow/chatflow target e2e')
} finally {
  await browser.close()
}
