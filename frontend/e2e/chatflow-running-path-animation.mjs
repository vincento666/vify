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

async function waitForRunResult(page, resultRef, label, timeout = 8000) {
  const deadline = Date.now() + timeout
  let latest = null
  while (Date.now() < deadline) {
    latest = await unwrap(await page.request.get(new URL(resultRef, baseUrl).toString()), `${label} result`)
    if (['SUCCEEDED', 'FAILED', 'INTERRUPTED', 'CANCELLED'].includes(String(latest.status || '').toUpperCase())) {
      return latest
    }
    await page.waitForTimeout(120)
  }
  throw new Error(`${label} did not finish before timeout: ${JSON.stringify(latest)}`)
}

async function edgeClasses(page, edgeId) {
  return page.evaluate((id) => {
    const element = document.querySelector(`.vue-flow__edge[data-id="${id}"] .coze-edge-path`)
    return element ? Array.from(element.classList) : []
  }, edgeId)
}

async function waitForEdgeClass(page, edgeId, className) {
  await page.waitForFunction(
    ({ id, expected }) => {
      const element = document.querySelector(`.vue-flow__edge[data-id="${id}"] .coze-edge-path`)
      return element?.classList.contains(expected)
    },
    { id: edgeId, expected: className },
    { timeout: 8000 },
  )
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const stamp = Date.now()
  const chatflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `025.5 Running Path ${stamp}`,
      description: 'running path animation e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
        { nodeKey: 'question_1', type: 'QUESTION', name: '问题', config: { question: '继续吗？', outputVariable: 'answer', ui: { position: { x: 500, y: 180 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'answer={{question_1.answer}}', ui: { position: { x: 880, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'question_1', condition: null },
        { sourceNodeKey: 'question_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create running chatflow')
  const interrupted = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs-legacy`, {
    data: {
      input: {
        'sys.query': 'start',
        'sys.conversation_id': `run-path-${stamp}`,
        'sys.user_id': 'uat',
        'sys.channel': 'web',
      },
    },
  }), 'run interrupted chatflow')
  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas?debug=1&runId=${interrupted.runId}`, { waitUntil: 'networkidle' })
  await waitForEdgeClass(page, 'start->question_1', 'edge-running')
  const runningClasses = await edgeClasses(page, 'start->question_1')
  assert(runningClasses.includes('edge-running'), `Expected interrupted question incoming edge to animate: ${runningClasses.join(' ')}`)

  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `025.5 Branch Path ${stamp}`,
      description: 'active branch edge e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 260 } } } },
        { nodeKey: 'router', type: 'CONDITION', name: '选择器', config: { expression: '{{start.intent}}', outputVariable: 'route', ui: { position: { x: 440, y: 260 } } } },
        { nodeKey: 'vip', type: 'TEXT_PROCESS', name: 'VIP', config: { operation: 'format_template', template: 'vip {{start.userMessage}}', outputVariable: 'answer', ui: { position: { x: 760, y: 160 } } } },
        { nodeKey: 'fallback', type: 'TEXT_PROCESS', name: '默认', config: { operation: 'format_template', template: 'fallback', outputVariable: 'answer', ui: { position: { x: 760, y: 360 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{vip.answer}}{{fallback.answer}}', ui: { position: { x: 1080, y: 260 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'router', condition: null },
        { sourceNodeKey: 'router', targetNodeKey: 'vip', condition: 'vip' },
        { sourceNodeKey: 'router', targetNodeKey: 'fallback', condition: null },
        { sourceNodeKey: 'vip', targetNodeKey: 'end', condition: null },
        { sourceNodeKey: 'fallback', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create branch workflow')
  const run = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
    data: { input: { userMessage: 'gold', USER_INPUT: 'gold', intent: 'vip' } },
  }), 'run branch workflow')
  const terminal = await waitForRunResult(page, run.resultRef, 'branch workflow')
  assert(terminal.status === 'SUCCEEDED', `Expected branch workflow to finish successfully: ${JSON.stringify(terminal)}`)
  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas?debug=1&runId=${run.runId}`, { waitUntil: 'networkidle' })
  await waitForEdgeClass(page, 'router->vip', 'edge-active-branch')
  await waitForEdgeClass(page, 'router->fallback', 'edge-inactive-branch')
  const activeClasses = await edgeClasses(page, 'router->vip')
  const inactiveClasses = await edgeClasses(page, 'router->fallback')
  assert(activeClasses.includes('edge-active-branch'), `Expected vip branch active: ${activeClasses.join(' ')}`)
  assert(inactiveClasses.includes('edge-inactive-branch'), `Expected fallback branch inactive: ${inactiveClasses.join(' ')}`)
  assert(!inactiveClasses.includes('edge-running'), `Expected inactive fallback not to animate: ${inactiveClasses.join(' ')}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS 025.5 running path animation e2e chatflow=${chatflow.id} workflow=${workflow.id}`)
} finally {
  await browser.close()
}
