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

function absoluteDebugUrl(debugUrl) {
  if (debugUrl.startsWith('http://') || debugUrl.startsWith('https://')) return debugUrl
  return `${baseUrl}${debugUrl}`
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  const stamp = Date.now()
  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `021.5 API Debug URL ${stamp}`,
      description: '',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 140, y: 180 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'answer', output: 'debug {{start.USER_INPUT}}', ui: { position: { x: 620, y: 180 } } } },
      ],
      edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
    },
  }), 'create workflow')
  const run = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
    data: { input: { USER_INPUT: 'api debug payload' } },
  }), 'run workflow')
  assert(run.debugUrl === `/workflows/${workflow.id}/canvas?runId=${run.runId}&debug=1`, `Unexpected debugUrl ${run.debugUrl}`)
  assert(run.debug_url === run.debugUrl, 'Expected snake_case debug_url alias')
  assert(!run.debugUrl.includes('payload'), 'debugUrl leaked raw payload')

  await page.goto(absoluteDebugUrl(run.debugUrl), { waitUntil: 'networkidle' })
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.waitFor({ state: 'visible', timeout: 10000 })
  const text = await dock.innerText()
  assert(text.includes(`Run #${run.runId}`), 'Expected returned debugUrl to open selected run')
  assert(text.includes('api debug payload'), 'Expected selected run detail payload in dock after opening debugUrl')
  assert(page.url().includes(`/workflows/${workflow.id}/canvas`), `Expected workflow canvas URL, got ${page.url()}`)
  assert(!page.url().includes('/observe'), `Expected no observe URL, got ${page.url()}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS composer debug URL API workflow=${workflow.id} run=${run.runId}`)
} finally {
  await browser.close()
}
