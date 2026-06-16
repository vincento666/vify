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
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } })

try {
  const stamp = Date.now()
  const conversationId = `observe-e2e-${stamp}`
  const userId = `observe-user-${stamp}`
  const chatflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `019.4 Observe E2E ${stamp}`,
      description: 'observe surfaces e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 160 } } } },
        {
          nodeKey: 'handoff_1',
          type: 'TRANSFER_TO_HUMAN',
          name: '转人工',
          config: {
            queue: 'observe-support',
            message: '已进入人工处理队列。',
            priority: 'high',
            ui: { position: { x: 480, y: 160 } },
          },
        },
        {
          nodeKey: 'end',
          type: 'END',
          name: '结束',
          config: { outputVariable: 'final', output: 'done', ui: { position: { x: 820, y: 160 } } },
        },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'handoff_1', condition: null },
        { sourceNodeKey: 'handoff_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create chatflow')

  const run = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
    data: {
      input: {
        'sys.query': '需要人工观察这个运行',
        'sys.conversation_id': conversationId,
        'sys.user_id': userId,
        'sys.channel': 'web',
      },
    },
  }), 'run chatflow')
  assert(run.status === 'INTERRUPTED', `Expected interrupted run, got ${run.status}`)

  const metrics = await unwrap(await page.request.get(`${baseUrl}/api/v1/observe/metrics`), 'observe metrics api')
  assert(metrics.runCount >= 1, 'Expected observe metrics to include at least one run')
  assert(metrics.handoffCount >= 1, 'Expected observe metrics to include handoffs')
  assert(metrics.channelDistribution.web >= 1, 'Expected web channel distribution')

  const detail = await unwrap(await page.request.get(`${baseUrl}/api/v1/observe/runs/${run.runId}`), 'observe run detail api')
  assert(detail.events.some((event) => event.type === 'handoff_requested'), 'Expected handoff_requested event')
  assert(detail.nodeRuns.some((node) => node.nodeKey === 'handoff_1'), 'Expected handoff node trace')

  const sessions = await unwrap(await page.request.get(`${baseUrl}/api/v1/observe/sessions?pageSize=50`), 'observe sessions api')
  const currentSession = sessions.list.find((item) => item.conversationId === conversationId)
  assert(currentSession, `Expected current observe session for ${conversationId}`)
  assert(String(currentSession.status).includes('handoff'), 'Expected current session to be in handoff state')

  await page.goto(`${baseUrl}/observe?runId=${run.runId}`, { waitUntil: 'networkidle' })
  await page.waitForURL(`${baseUrl}/chatflows/${chatflow.id}/canvas?runId=${run.runId}&debug=1`, { timeout: 10000 })
  assert(!page.url().includes('/observe'), `Expected observe route to redirect to composer, got ${page.url()}`)
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.getByText(`Run #${run.runId}`, { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  const detailText = await dock.textContent()
  assert(detailText.includes('handoff_1'), 'Expected embedded trace detail to include handoff_1')
  assert(detailText.includes('转人工'), 'Expected embedded trace detail to include handoff event')
  assert(await page.getByTestId('observe-run-detail').count() === 0, 'Standalone observe detail should not render')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS observe surfaces e2e chatflow=${chatflow.id} run=${run.runId}`)
} finally {
  await browser.close()
}
