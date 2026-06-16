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
  await panel.getByTestId('chatflow-run-fields-toggle').click()
  await panel.getByPlaceholder('输入消息').fill('我要升级为人工客服')
  await panel.getByPlaceholder('conversation_id').fill(conversationId)
  await panel.getByPlaceholder('user_id').fill(`vip-user-${stamp}`)
  await panel.getByRole('button', { name: '发送消息', exact: true }).click()

  await panel.getByText('INTERRUPTED', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByText('已为你转接 VIP 人工客服，请稍候。', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })

  await page.getByRole('button', { name: '调试工具', exact: true }).click()
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.getByText('高级运行上下文').click()
  await dock.getByText('事件时间线').waitFor({ state: 'visible', timeout: 10000 })
  await dock.getByText('转人工', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await dock.getByText(/工单 #\d+ · vip-support/).waitFor({ state: 'visible', timeout: 10000 })

  const handoffs = await unwrap(await page.request.get(`${baseUrl}/api/v1/handoffs?status=queued&pageSize=100`), 'list handoffs')
  const ticket = handoffs.list.find((item) => item.conversationId === conversationId)
  assert(ticket, `Expected queued handoff ticket for ${conversationId}`)
  assert(ticket.queue === 'vip-support', `Expected vip-support queue, got ${ticket.queue}`)
  assert(ticket.priority === 'high', `Expected high priority, got ${ticket.priority}`)
  assert(ticket.status === 'queued', `Expected queued status, got ${ticket.status}`)
  assert(ticket.transcriptSnapshot.some((entry) => entry.content === '我要升级为人工客服'), 'Expected transcript to include user request')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS chatflow transfer to human e2e chatflow=${chatflow.id} ticket=${ticket.id}`)
} finally {
  await browser.close()
}
