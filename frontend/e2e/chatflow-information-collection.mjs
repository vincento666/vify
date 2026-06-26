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
        name: `015.5 Information Collection ${Date.now()}`,
        description: 'smart slot collection e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 120, y: 180 } } } },
          {
            nodeKey: 'info_1',
            type: 'INFORMATION_COLLECTION',
            name: '信息收集',
            config: {
              inputSource: '{{start.sys.query}}',
              outputVariable: 'profile',
              collectionKey: 'profile',
              includeHistory: true,
              extractorMode: 'fake',
              maxRounds: 3,
              streamOutput: 'enabled',
              fields: [
                { name: 'name', type: 'string', required: true, description: '姓名', targetScope: 'conversation', targetVariable: 'customer_name' },
                { name: 'phone', type: 'string', required: true, description: '手机号' },
              ],
              ui: { position: { x: 420, y: 160 } },
            },
          },
          {
            nodeKey: 'message_1',
            type: 'MESSAGE',
            name: '确认消息',
            config: { content: '已收集 {{info_1.name}} {{info_1.phone}} {{conversation.customer_name}}', outputVariable: 'content', streamOutput: 'enabled', ui: { position: { x: 760, y: 160 } } },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{message_1.content}}', ui: { position: { x: 1080, y: 160 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'info_1', condition: null },
          { sourceNodeKey: 'info_1', targetNodeKey: 'message_1', condition: null },
          { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create information collection chatflow',
  )

  const interrupted = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs-legacy`, {
      data: { input: { 'sys.query': '我叫 Ada' } },
    }),
    'run incomplete collection',
  )
  assert(interrupted.status === 'INTERRUPTED', `Expected INTERRUPTED, got ${interrupted.status}`)
  assert(interrupted.output.interrupt.nodeKey === 'info_1', 'Expected information collection interrupt')
  assert(interrupted.output.collected.name === 'Ada', 'Expected name collected from first message')
  assert(interrupted.output.missing.join(',') === 'phone', 'Expected phone missing')
  assert(interrupted.output.events.map((event) => event.type).join(',') === 'message_delta,message_done,interrupt', 'Expected streaming follow-up events')

  const resumed = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs-legacy`, {
      data: {
        input: {
          'sys.query': '手机号 13800138000',
          resume: { info_1: { answer: '手机号 13800138000', collected: { name: 'Ada' } } },
        },
      },
    }),
    'resume completed collection',
  )
  assert(resumed.status === 'SUCCEEDED', `Expected SUCCEEDED, got ${resumed.status}`)
  assert(resumed.output.final === '已收集 Ada 13800138000 Ada', `Unexpected final output ${JSON.stringify(resumed.output)}`)

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-information_collection').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.coze-node.node-message').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.coze-node.node-information_collection').click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const panelText = await panel.innerText()
  assert(panelText.includes('收集策略'), 'Expected collection strategy section')
  assert(panelText.includes('收集字段'), 'Expected collection fields section')
  await panel.locator('[data-testid="collection-field-editor"]').waitFor({ state: 'visible', timeout: 5000 })
  assert(await panel.locator('[data-testid="collection-field-row"]').count() >= 2, 'Expected structured field rows')
  assert(panelText.includes('会话历史感知'), 'Expected history awareness config')
  assert(panelText.includes('写入会话上下文'), 'Expected context write toggle')
  assert(panelText.includes('最大收集轮次'), 'Expected max rounds config')
  assert(panelText.includes('追问流式输出'), 'Expected streaming follow-up config')
  assert(panelText.includes('输出变量'), 'Expected output variable controls')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow information collection e2e')
} finally {
  await browser.close()
}
