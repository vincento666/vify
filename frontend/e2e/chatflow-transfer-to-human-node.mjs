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
  const conversationId = `handoff-e2e-${stamp}`
  const chatflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `019.1 Transfer To Human ${stamp}`,
      description: 'transfer to human e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'transfer_to_human_1',
          type: 'TRANSFER_TO_HUMAN',
          name: '转人工',
          config: {
            message: '已为你转接 VIP 人工客服，请稍候。',
            queue: 'vip-support',
            reason: 'vip_escalation',
            priority: 'high',
            slaMinutes: 15,
            outputParameters: [
              { name: 'handoff_id', type: 'number' },
              { name: 'handoff_status', type: 'string' },
              { name: 'queue', type: 'string' },
              { name: 'priority', type: 'string' },
            ],
            ui: { position: { x: 520, y: 180 } },
          },
        },
        {
          nodeKey: 'end',
          type: 'END',
          name: '结束',
          config: {
            outputVariable: 'final',
            output: 'handoff={{transfer_to_human_1.handoff_status}}',
            ui: { position: { x: 900, y: 180 } },
          },
        },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'transfer_to_human_1', condition: null },
        { sourceNodeKey: 'transfer_to_human_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create chatflow')

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  const transferNode = page.locator('.coze-node.node-transfer_to_human')
  assert(await transferNode.count() === 1, 'Expected one transfer-to-human canvas node')
  await transferNode.click()
  const configPanel = page.getByTestId('node-config-panel')
  await configPanel.getByText('转接配置').waitFor({ state: 'visible', timeout: 8000 })
  await configPanel.getByText('队列').waitFor({ state: 'visible', timeout: 8000 })
  await configPanel.getByText('优先级').waitFor({ state: 'visible', timeout: 8000 })

  await page.getByRole('button', { name: '对话试运行', exact: true }).click()
  const panel = page.getByTestId('test-run-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByRole('button', { name: '对话设置', exact: true }).click()
  await panel.getByPlaceholder('conversation_id').fill(conversationId)
  await panel.getByPlaceholder('user_id').fill(`vip-user-${stamp}`)
  await panel.getByTestId('chatflow-run-message-input').fill('我要升级为人工客服')
  await panel.getByRole('button', { name: '发送消息', exact: true }).click()

  await panel.getByText('INTERRUPTED', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByText('已为你转接 VIP 人工客服，请稍候。', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  const runLabel = await panel.getByText(/Run #\d+/).first().textContent()
  const runId = Number(runLabel?.match(/Run #(\d+)/)?.[1] || 0)
  assert(runId > 0, `Expected runtime v2 run id in panel, got ${runLabel}`)

  await page.getByRole('button', { name: '调试工具', exact: true }).click()
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.getByText('高级运行上下文').click()
  await dock.getByText('事件时间线').waitFor({ state: 'visible', timeout: 10000 })
  await dock.getByTestId('chatflow-run-call-tree').getByText('transfer_to_human_1', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await dock.getByText(/工单 #runtime-v2-handoff-\d+-transfer_to_human_1 · vip-support · waiting/).waitFor({ state: 'visible', timeout: 10000 })

  const runtimeRun = await unwrap(await page.request.get(`${baseUrl}/api/v1/runtime-runs/${runId}`), 'get runtime v2 run')
  assert(runtimeRun.status === 'INTERRUPTED', `Expected interrupted runtime run, got ${runtimeRun.status}`)
  assert(runtimeRun.output?.interrupt?.type === 'TRANSFER_TO_HUMAN', 'Expected transfer-to-human interrupt output')
  assert(runtimeRun.output?.interrupt?.queue === 'vip-support', `Expected vip-support interrupt queue, got ${runtimeRun.output?.interrupt?.queue}`)

  const runtimeEvents = await unwrap(await page.request.get(`${baseUrl}/api/v1/runtime-runs/${runId}/events`), 'list runtime v2 events')
  const handoffEvent = runtimeEvents.list.find((event) => event.type === 'handoff_requested')
  assert(handoffEvent, `Expected runtime v2 handoff_requested event for run ${runId}`)
  assert(handoffEvent.nodeId === 'transfer_to_human_1', `Expected handoff node id, got ${handoffEvent.nodeId}`)
  assert(handoffEvent.payload?.queue === 'vip-support', `Expected vip-support event queue, got ${handoffEvent.payload?.queue}`)
  assert(handoffEvent.payload?.priority === 'high', `Expected high event priority, got ${handoffEvent.payload?.priority}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS chatflow transfer to human e2e chatflow=${chatflow.id} run=${runId} handoff=${handoffEvent.payload?.handoffId}`)
} finally {
  await browser.close()
}
