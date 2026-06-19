import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const artifactDir = process.env.HIFY_E2E_ARTIFACT_DIR || '/Users/vincento/work/develop/hify/artifacts/slices/196-chatflow-session-message-gateway/196.1'
const screenshotDir = process.env.HIFY_E2E_SCREENSHOT_DIR || join(artifactDir, 'screenshots')
const reportPath = process.env.HIFY_E2E_REPORT || join(artifactDir, 'chatflow-session-gateway-uat.json')

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  const text = await response.text()
  let payload = {}
  try {
    payload = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`${label} returned non-JSON HTTP ${response.status()}: ${text}`)
  }
  assert(response.ok(), `${label} HTTP ${response.status()}: ${text}`)
  assert(payload.code === 200, `${label} API ${payload.message || text}`)
  return payload.data
}

async function requestJson(page, path, data, label) {
  return unwrap(await page.request.post(`${baseUrl}${path}`, { data }), label)
}

async function getJson(page, path, label) {
  return unwrap(await page.request.get(`${baseUrl}${path}`), label)
}

function createChatflowPayload(stamp) {
  return {
    name: `196.1 Chatflow Session Gateway UAT ${stamp}`,
    description: 'message-first gateway browser UAT',
    nodes: [
      { nodeKey: 'start', type: 'START', name: 'Start', config: {} },
      {
        nodeKey: 'message_1',
        type: 'MESSAGE',
        name: 'Message',
        config: { content: 'Hello {{start.sys.query}}', outputVariable: 'content' },
      },
      {
        nodeKey: 'end',
        type: 'END',
        name: 'End',
        config: { outputVariable: 'answer', output: 'answer: {{message_1.content}}' },
      },
    ],
    edges: [
      { sourceNodeKey: 'start', targetNodeKey: 'message_1', condition: null },
      { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
    ],
  }
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1280, height: 860 } })

try {
  await mkdir(screenshotDir, { recursive: true })
  const stamp = Date.now()
  const chatflow = await requestJson(page, '/api/v1/chatflows', createChatflowPayload(stamp), 'create chatflow')
  const first = await requestJson(page, `/api/v1/chatflows/${chatflow.id}/messages`, {
    message: 'first browser turn',
    userId: 'browser-uat-user',
    channel: 'browser-uat',
    waitTimeoutMs: 1200,
    idempotencyKey: `uat-first-${stamp}`,
  }, 'send first message')
  const second = await requestJson(page, `/api/v1/chatflows/${chatflow.id}/messages`, {
    message: 'second browser turn',
    sessionId: first.sessionId,
    userId: 'browser-uat-user',
    channel: 'browser-uat',
    waitTimeoutMs: 1200,
    idempotencyKey: `uat-second-${stamp}`,
  }, 'send second message')
  const replay = await requestJson(page, `/api/v1/chatflows/${chatflow.id}/messages`, {
    message: 'second browser turn',
    sessionId: first.sessionId,
    userId: 'browser-uat-user',
    channel: 'browser-uat',
    waitTimeoutMs: 1200,
    idempotencyKey: `uat-second-${stamp}`,
  }, 'replay second message')
  const session = await getJson(page, `/api/v1/chatflows/${chatflow.id}/sessions/${first.sessionId}`, 'get chatflow session')
  const sessionEvents = await getJson(page, `/api/v1/chatflows/${chatflow.id}/sessions/${first.sessionId}/events`, 'get session events')
  const secondRunEvents = await getJson(page, `/api/v1/chatflows/${chatflow.id}/runs/${second.runId}/events`, 'get second run events')

  assert(first.status === 'SUCCEEDED', `first turn should complete: ${JSON.stringify(first)}`)
  assert(second.status === 'SUCCEEDED', `second turn should complete: ${JSON.stringify(second)}`)
  assert(first.sessionId && second.sessionId === first.sessionId, 'second turn should reuse first session')
  assert(second.runId !== first.runId, 'second turn should create a new runtime run')
  assert(replay.runId === second.runId && replay.idempotentReplay === true, `replay should return same run: ${JSON.stringify(replay)}`)
  assert(first.answer === 'answer: Hello first browser turn', `unexpected first answer: ${first.answer}`)
  assert(second.answer === 'answer: Hello second browser turn', `unexpected second answer: ${second.answer}`)
  assert(session.currentRunId === second.runId, `session should point at second run: ${JSON.stringify(session)}`)
  const sessionRunIds = new Set(sessionEvents.list.map((event) => event.runId))
  assert(sessionRunIds.has(first.runId) && sessionRunIds.has(second.runId), `session events should include both turns: ${JSON.stringify(sessionEvents)}`)
  const secondTypes = secondRunEvents.list.map((event) => event.type)
  assert(secondTypes.includes('user_message') && secondTypes.includes('assistant_message'), `second run should include message events: ${JSON.stringify(secondRunEvents)}`)

  const report = {
    chatflowId: chatflow.id,
    sessionId: first.sessionId,
    first,
    second,
    replay,
    session,
    sessionEventsTotal: sessionEvents.total,
    secondRunEventTypes: secondTypes,
  }
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`)
  await page.setContent(`
    <main style="font-family: system-ui; padding: 2rem; line-height: 1.45;">
      <h1>Chatflow Session Gateway UAT</h1>
      <p>Chatflow #${chatflow.id}</p>
      <p>Session ${first.sessionId}</p>
      <p>First answer: ${first.answer}</p>
      <p>Second answer: ${second.answer}</p>
      <p>Replay run: ${replay.runId}</p>
    </main>
  `)
  const screenshot = join(screenshotDir, 'chatflow-session-gateway.png')
  await page.screenshot({ path: screenshot, fullPage: true })
  console.log(`PASS chatflow session gateway UAT chatflow=${chatflow.id} session=${first.sessionId} screenshot=${screenshot}`)
} finally {
  await browser.close()
}
