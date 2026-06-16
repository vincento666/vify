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

async function seedComparableRuns() {
  const workflow = await api('/workflows', {
    method: 'POST',
    body: JSON.stringify({
      name: `E2E Compare Workflow ${suffix}`,
      description: '',
      nodes: [
        { nodeKey: 'start', type: 'START', name: 'Start', config: {} },
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
    body: JSON.stringify({ name: `E2E Compare Set ${suffix}`, description: 'compare e2e' }),
  })
  const cases = []
  for (const [input, expected] of [
    ['alpha', 'LLM mock: Workflow says alpha'],
    ['beta', 'wrong beta'],
    ['gamma', 'wrong gamma'],
    ['delta', 'wrong delta'],
  ]) {
    cases.push(await api(`/eval-sets/${evalSet.id}/cases`, {
      method: 'POST',
      body: JSON.stringify({ input, expectedOutput: expected, tags: ['compare'] }),
    }))
  }
  const evaluator = await api('/evaluators', {
    method: 'POST',
    body: JSON.stringify({ name: `E2E Compare Exact ${suffix}`, type: 'EXACT_MATCH', config: {} }),
  })
  const experiment = await api('/evaluation-experiments', {
    method: 'POST',
    body: JSON.stringify({
      name: `E2E Compare Experiment ${suffix}`,
      targetType: 'WORKFLOW',
      targetId: workflow.id,
      evalSetId: evalSet.id,
      evaluatorIds: [evaluator.id],
    }),
  })
  const baseRun = await api(`/evaluation-experiments/${experiment.id}/runs`, { method: 'POST', body: '{}' })

  const candidateExpectations = [
    ['alpha', 'wrong alpha'],
    ['beta', 'LLM mock: Workflow says beta'],
    ['gamma', 'wrong gamma'],
    ['delta', 'LLM mock: Workflow says delta'],
  ]
  for (let index = 0; index < cases.length; index += 1) {
    await api(`/eval-cases/${cases[index].id}`, {
      method: 'PUT',
      body: JSON.stringify({
        input: candidateExpectations[index][0],
        expectedOutput: candidateExpectations[index][1],
        tags: ['compare'],
      }),
    })
  }
  const candidateRun = await api(`/evaluation-experiments/${experiment.id}/runs`, { method: 'POST', body: '{}' })
  assert(baseRun.passedCases === 1, 'Expected base run to pass one case')
  assert(candidateRun.passedCases === 2, 'Expected candidate run to pass two cases')
  return { baseRun, candidateRun }
}

async function assertBodyIncludes(page, text) {
  const body = await page.locator('body').innerText()
  assert(body.includes(text), `Expected page body to include: ${text}`)
}

const { baseRun, candidateRun } = await seedComparableRuns()
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  await page.goto(`${baseUrl}/evaluation`, { waitUntil: 'networkidle' })
  await page.getByRole('tab', { name: '对比分析' }).click()
  await page.getByTestId('compare-base-run').selectOption(String(baseRun.id))
  await page.getByTestId('compare-candidate-run').selectOption(String(candidateRun.id))
  await page.getByTestId('run-compare').click()

  await page.getByText('分数变化').waitFor({ state: 'visible', timeout: 10000 })
  await assertBodyIncludes(page, '+25.0%')
  await assertBodyIncludes(page, '新增失败 1')
  await assertBodyIncludes(page, '恢复通过 2')
  await assertBodyIncludes(page, '持续失败 1')
  await assertBodyIncludes(page, 'alpha')
  await assertBodyIncludes(page, 'beta')
  await assertBodyIncludes(page, 'gamma')
  await assertBodyIncludes(page, 'delta')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS evaluation compare analysis e2e')
} finally {
  await browser.close()
}
