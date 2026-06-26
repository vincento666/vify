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

async function readEnvelope(response) {
  return { httpStatus: response.status(), payload: await response.json() }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 820 } })

try {
  const stamp = Date.now()
  const chatflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `018.5 Resume Reliability ${stamp}`,
      description: 'resume reliability e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
        { nodeKey: 'question_1', type: 'QUESTION', name: '问题', config: { question: '主题？', outputVariable: 'answer', ui: { position: { x: 500, y: 180 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'topic={{question_1.answer}}', ui: { position: { x: 880, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'question_1', condition: null },
        { sourceNodeKey: 'question_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create chatflow')

  const interrupted = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs-legacy`, {
    data: { input: { 'sys.query': 'start', 'sys.conversation_id': `resume-reliability-${stamp}` } },
  }), 'start chatflow')
  assert(interrupted.status === 'INTERRUPTED', 'Expected interrupted run')
  const runId = interrupted.runId
  const eventId = interrupted.events[interrupted.events.length - 1].id

  const wrongEvent = await readEnvelope(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs/${runId}/resume`, {
    data: { eventId: eventId + 1000, resumeData: { answer: 'refund' } },
  }))
  assert(wrongEvent.httpStatus === 404, `Expected wrong event HTTP 404, got ${JSON.stringify(wrongEvent)}`)
  assert(wrongEvent.payload.code === 404, `Expected wrong event rejected, got ${JSON.stringify(wrongEvent)}`)

  const first = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs/${runId}/resume`, {
    data: { eventId, resumeData: { answer: 'refund' }, idempotencyKey: `idem-${stamp}` },
  }), 'first resume')
  const replay = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs/${runId}/resume`, {
    data: { eventId, resumeData: { answer: 'refund' }, idempotencyKey: `idem-${stamp}` },
  }), 'replay resume')
  assert(first.status === 'SUCCEEDED', 'Expected first resume succeeded')
  assert(replay.status === 'SUCCEEDED', 'Expected replay resume succeeded')
  assert(replay.output.final === first.output.final, 'Expected replay output to match first resume')
  assert(replay.events.some((event) => event.type === 'resume'), 'Expected replay to expose event history')

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-question').waitFor({ state: 'visible', timeout: 10000 })
  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS chatflow resume reliability e2e chatflow=${chatflow.id} run=${runId}`)
} finally {
  await browser.close()
}
