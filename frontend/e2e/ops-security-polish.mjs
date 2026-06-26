import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function envelope(response, label) {
  const payload = await response.json()
  return { ok: response.ok(), status: response.status(), payload, label }
}

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function createHandoffChatflow(page, name, { queue = 'security', slaMinutes = 1 } = {}) {
  return unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name,
      description: '019.5 ops/security fixture',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'handoff_1',
          type: 'TRANSFER_TO_HUMAN',
          name: '转人工',
          config: {
            queue,
            message: '转人工',
            slaMinutes,
            ui: { position: { x: 500, y: 180 } },
          },
        },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'done', ui: { position: { x: 860, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'handoff_1', condition: null },
        { sourceNodeKey: 'handoff_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), `create ${name}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  const stamp = Date.now()
  const invalid = await createHandoffChatflow(page, `019.5 Invalid Publish ${stamp}`, { queue: '' })
  const publishFailure = await envelope(await page.request.post(`${baseUrl}/api/v1/chatflows/${invalid.id}/publish`), 'publish failure')
  assert(publishFailure.status === 400, `Expected publish failure, got ${publishFailure.status}`)
  assert(String(publishFailure.payload.message).includes('handoff queue'), 'Expected publish failure to mention handoff queue')

  const disabled = await createHandoffChatflow(page, `019.5 Disabled Channel ${stamp}`)
  await unwrap(await page.request.put(`${baseUrl}/api/v1/chatflows/${disabled.id}/channels/web`, {
    data: { displayName: 'Disabled Web', enabled: false, config: { channelId: 'web-disabled' } },
  }), 'disable web channel')
  const disabledFailure = await envelope(await page.request.post(`${baseUrl}/api/v1/chatflows/${disabled.id}/channels/web/test`, {
    data: { message: 'hello', conversationId: `disabled-${stamp}` },
  }), 'disabled channel test')
  assert(disabledFailure.status === 400, `Expected disabled channel failure, got ${disabledFailure.status}`)
  assert(String(disabledFailure.payload.message).includes('disabled'), 'Expected disabled channel message')

  const secure = await createHandoffChatflow(page, `019.5 Secure Handoff ${stamp}`)
  const conversationId = `ops-sec-${stamp}`
  const run = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${secure.id}/runs-legacy`, {
    data: {
      input: {
        'sys.query': '请转人工 apiKey=sk-secret password=hunter2',
        'sys.conversation_id': conversationId,
        'sys.user_id': `secure-user-${stamp}`,
        'sys.channel': 'web',
      },
    },
  }), 'run secure handoff')

  const handoffs = await unwrap(await page.request.get(`${baseUrl}/api/v1/handoffs?pageSize=100`), 'list handoffs')
  const ticket = handoffs.list.find((item) => item.conversationId === conversationId)
  assert(ticket, `Expected handoff ticket for ${conversationId}`)
  assert(ticket.slaState === 'warning', `Expected warning SLA state, got ${ticket.slaState}`)
  const transcriptText = JSON.stringify(ticket.transcriptSnapshot)
  assert(transcriptText.includes('***'), 'Expected sanitized transcript marker')
  assert(!transcriptText.includes('sk-secret'), 'Transcript leaked api key')
  assert(!transcriptText.includes('hunter2'), 'Transcript leaked password')

  const audit = await unwrap(await page.request.get(`${baseUrl}/api/v1/audit-records?resourceType=CHATFLOW_CHANNEL&pageSize=100`), 'audit records')
  const failed = audit.list.find((item) => item.action === 'CHANNEL_DELIVERY_FAILED' && item.resourceId === `${disabled.id}:web`)
  assert(failed, 'Expected channel delivery failure audit')
  assert(failed.status === 'failed', 'Expected failed audit status')

  const metrics = await unwrap(await page.request.get(`${baseUrl}/api/v1/observe/metrics`), 'observe metrics')
  assert(metrics.channelDeliveryFailures >= 1, 'Expected observe metrics channelDeliveryFailures')

  const observeDetail = await unwrap(await page.request.get(`${baseUrl}/api/v1/observe/runs/${run.runId}`), 'observe run detail')
  const observeText = JSON.stringify(observeDetail)
  assert(observeText.includes('apiKey=***'), 'Expected sanitized observe run input marker')
  assert(!observeText.includes('sk-secret'), 'Observe detail leaked api key')
  assert(!observeText.includes('hunter2'), 'Observe detail leaked password')

  await page.goto(`${baseUrl}/observe?runId=${run.runId}`, { waitUntil: 'networkidle' })
  await page.waitForURL(`${baseUrl}/chatflows/${secure.id}/canvas?runId=${run.runId}&debug=1`, { timeout: 10000 })
  assert(!page.url().includes('/observe'), `Expected observe route to redirect to composer, got ${page.url()}`)
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.getByText(`Run #${run.runId}`, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS ops security polish e2e run=${run.runId} ticket=${ticket.id}`)
} finally {
  await browser.close()
}
