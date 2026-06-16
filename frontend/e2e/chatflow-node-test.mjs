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
        name: `Chatflow Node Test ${Date.now()}`,
        description: 'chatflow selected node profile e2e',
        nodes: [
          {
            nodeKey: 'start',
            type: 'START',
            name: '开始',
            config: {
              outputVariables: ['sys.query', 'sys.conversation_id', 'sys.user_id', 'sys.channel', 'sys.round'],
              ui: { position: { x: 160, y: 180 } },
            },
          },
          {
            nodeKey: 'message',
            type: 'MESSAGE',
            name: '消息',
            config: {
              content: 'CHATFLOW_NODE_PROFILE_OK {{sys.query}}',
              outputVariable: 'content',
              ui: { position: { x: 520, y: 160 } },
            },
          },
          {
            nodeKey: 'end',
            type: 'END',
            name: '结束',
            config: {
              outputVariable: 'answer',
              output: 'DOWNSTREAM {{message.content}}',
              ui: { position: { x: 860, y: 180 } },
            },
          },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'message', condition: null },
          { sourceNodeKey: 'message', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create chatflow node test flow',
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-message').click()
  const configPanel = page.getByTestId('node-config-panel')
  await configPanel.waitFor({ state: 'visible', timeout: 5000 })
  await configPanel.getByLabel('试运行当前节点').click()

  const drawer = page.locator('[data-testid="node-test-drawer"]')
  await drawer.waitFor({ state: 'visible', timeout: 5000 })
  const drawerText = await drawer.innerText()
  for (const label of ['试运行', '查看日志', '试运行输入']) {
    assert(drawerText.includes(label), `Expected chatflow node drawer to include ${label}, got ${drawerText}`)
  }
  for (const label of ['JSON模式', 'AI 补全']) {
    assert(!drawerText.includes(label), `Expected chatflow node drawer not to include ${label}, got ${drawerText}`)
  }
  assert(drawerText.includes('sys.query'), 'Expected sys.query fixture row')
  assert(drawerText.includes('sys.conversation_id'), 'Expected sys.conversation_id fixture row')
  assert(drawerText.includes('sys.user_id'), 'Expected sys.user_id fixture row')
  assert(drawerText.includes('sys.channel'), 'Expected sys.channel fixture row')

  await drawer.locator('.node-test-input-row', { hasText: 'sys.query' }).locator('input').fill('单节点 Chatflow profile 验收')
  await drawer.getByRole('button', { name: '运行', exact: true }).click()
  await drawer.getByText('SUCCEEDED').waitFor({ state: 'visible', timeout: 60000 })
  const resultText = await drawer.innerText()
  assert(resultText.includes('CHATFLOW_NODE_PROFILE_OK'), `Expected LLM node result, got ${resultText}`)
  assert(!resultText.includes('DOWNSTREAM'), 'Expected selected-node run not to continue downstream')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow selected-node profile e2e')
} finally {
  await browser.close()
}
