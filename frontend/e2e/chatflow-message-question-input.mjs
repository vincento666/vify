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
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `015.4 Message Question Input ${Date.now()}`,
        description: 'chat message question human input e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 120, y: 160 } } } },
          { nodeKey: 'message_1', type: 'MESSAGE', name: '消息', config: { content: 'Hello {{start.sys.query}}', outputVariable: 'content', streamOutput: 'enabled', ui: { position: { x: 440, y: 60 } } } },
          { nodeKey: 'question_1', type: 'QUESTION', name: '问题', config: { question: '继续吗？', outputVariable: 'answer', answerType: 'text', ui: { position: { x: 440, y: 220 } } } },
          {
            nodeKey: 'human_input_1',
            type: 'HUMAN_INPUT',
            name: '人工输入',
            config: {
              prompt: '请审核',
              outputVariable: 'payload',
              inputSchema: [
                { name: 'approved', type: 'boolean', required: true, description: '是否通过' },
                { name: 'note', type: 'string', required: false, description: '备注' },
              ],
              ui: { position: { x: 440, y: 380 } },
            },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'message={{message_1.content}} answer={{question_1.answer}} approved={{human_input_1.approved}}', ui: { position: { x: 900, y: 220 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'message_1', condition: null },
          { sourceNodeKey: 'message_1', targetNodeKey: 'question_1', condition: null },
          { sourceNodeKey: 'question_1', targetNodeKey: 'human_input_1', condition: null },
          { sourceNodeKey: 'human_input_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create chatflow message/question/input',
  )

  const messageNode = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/nodes/message_1/runs`, {
      data: { input: { 'sys.query': 'Ada' } },
    }),
    'selected message node run',
  )
  assert(messageNode.output.events.map((event) => event.type).join(',') === 'message_delta,message_done', 'Expected message streaming events')

  const interrupted = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
      data: { input: { 'sys.query': 'Ada' } },
    }),
    'interrupt run',
  )
  assert(interrupted.status === 'INTERRUPTED', `Expected INTERRUPTED, got ${interrupted.status}`)
  assert(interrupted.output.interrupt.nodeKey === 'question_1', 'Expected question interrupt')

  const resumed = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
      data: {
        input: {
          'sys.query': 'Ada',
          resume: {
            question_1: { answer: 'yes' },
            human_input_1: { payload: { approved: true } },
          },
        },
      },
    }),
    'resume run',
  )
  assert(resumed.status === 'SUCCEEDED', `Expected SUCCEEDED, got ${resumed.status}`)
  assert(resumed.output.final === 'message=Hello Ada answer=yes approved=True', `Unexpected resumed output ${JSON.stringify(resumed.output)}`)

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-message').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.coze-node.node-question').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.coze-node.node-human_input').waitFor({ state: 'visible', timeout: 10000 })

  await page.locator('.coze-node.node-question').click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  let panelText = await panel.innerText()
  assert(panelText.includes('提问并等待'), 'Expected wait-for-answer section')
  assert(panelText.includes('问题内容'), 'Expected question content config')
  assert(panelText.includes('答案类型'), 'Expected answer type config')
  assert(panelText.includes('回答选项'), 'Expected structured option section')
  await panel.locator('[data-testid="question-option-editor"]').waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByRole('button', { name: '添加回答选项' }).click()
  assert(await panel.locator('[data-testid="question-option-row"]').count() === 1, 'Expected option row editor')

  await page.locator('.coze-node.node-human_input').click()
  panelText = await panel.innerText()
  assert(panelText.includes('提示内容'), 'Expected human input prompt config')
  assert(panelText.includes('审批模式'), 'Expected human input approval mode config')
  assert(await panel.locator('[data-testid="human-input-schema-editor"]').count() === 1, 'Expected structured human input schema editor')
  assert(await panel.locator('[data-testid="human-input-schema-row"]').count() === 2, 'Expected human input schema rows')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow message question human input e2e')
} finally {
  await browser.close()
}
