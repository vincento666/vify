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
const page = await browser.newPage({ viewport: { width: 1280, height: 820 } })

try {
  const stamp = Date.now()
  const chatflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `018.2 Resume ${stamp}`,
      description: 'chatflow resume e2e',
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
  }), 'create chatflow')

  const interrupted = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs-legacy`, {
    data: {
      input: {
        'sys.query': 'start',
        'sys.conversation_id': `conv-${stamp}`,
        'sys.user_id': 'user-e2e',
        'sys.channel': 'web',
      },
    },
  }), 'start chatflow')
  assert(interrupted.status === 'INTERRUPTED', 'Expected interrupted start')
  const runId = interrupted.runId
  const eventId = interrupted.events[interrupted.events.length - 1].id

  const resumed = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs/${runId}/resume`, {
    data: { eventId, resumeData: { answer: 'yes' } },
  }), 'resume chatflow')
  assert(resumed.runId === runId, 'Expected same run id')
  assert(resumed.status === 'SUCCEEDED', 'Expected resumed run succeeded')
  assert(resumed.output.final === 'answer=yes', 'Expected resumed output')

  const events = await unwrap(await page.request.get(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs/${runId}/events`), 'list events')
  assert(events.list.map((event) => event.type).join(',') === 'message,interrupt,resume,done', 'Expected full resume event sequence')

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-question').waitFor({ state: 'visible', timeout: 10000 })
  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS chatflow resume api e2e chatflow=${chatflow.id} run=${runId}`)
} finally {
  await browser.close()
}
