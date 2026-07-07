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
  const chatflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `018.4 Timeline UI ${stamp}`,
      description: 'chatflow runtime timeline ui e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
        { nodeKey: 'question_1', type: 'QUESTION', name: '问题', config: { question: '主题？', outputVariable: 'answer', ui: { position: { x: 460, y: 180 } } } },
        {
          nodeKey: 'assign_1',
          type: 'VARIABLE_ASSIGN',
          name: '变量赋值',
          config: {
            targetScope: 'conversation',
            targetVariable: 'topic',
            source: '{{question_1.answer}}',
            outputParameters: [{ name: 'assigned', type: 'string' }],
            ui: { position: { x: 780, y: 180 } },
          },
        },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'topic={{conversation.topic}}', ui: { position: { x: 1120, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'question_1', condition: null },
        { sourceNodeKey: 'question_1', targetNodeKey: 'assign_1', condition: null },
        { sourceNodeKey: 'assign_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create chatflow')

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '对话试运行', exact: true }).click()
  const panel = page.getByTestId('test-run-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByTestId('chatflow-run-message-input').fill('start')
  await panel.getByRole('button', { name: '发送消息', exact: true }).click()
  await panel.getByText('主题？', { exact: true }).waitFor({ state: 'visible', timeout: 8000 })

  await page.getByRole('button', { name: '调试工具', exact: true }).click()
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.getByText('高级运行上下文').click()
  const timeline = dock.getByTestId('chatflow-event-timeline')
  await timeline.getByText('事件时间线').waitFor({ state: 'visible', timeout: 8000 })
  const waitingState = dock.getByTestId('chatflow-waiting-state')
  await waitingState.getByText('question_1').waitFor({ state: 'visible', timeout: 8000 })
  await timeline.getByText('等待输入').waitFor({ state: 'visible', timeout: 8000 })
  await waitingState.getByText('请按下方表单补充信息', { exact: false }).waitFor({ state: 'visible', timeout: 8000 })
  await dock.getByLabel('回复内容').fill('refund')
  await dock.getByRole('button', { name: '提交回复继续', exact: true }).click()

  await timeline.getByText('继续执行').waitFor({ state: 'visible', timeout: 8000 })
  await timeline.getByText('运行完成', { exact: true }).waitFor({ state: 'visible', timeout: 8000 })
  await dock.getByText('conversation.topic', { exact: true }).waitFor({ state: 'visible', timeout: 8000 })
  await dock.getByText('refund', { exact: true }).waitFor({ state: 'visible', timeout: 8000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS chatflow runtime timeline ui e2e chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
