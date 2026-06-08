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
  const stamp = Date.now()
  const chatflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows`, {
    data: {
      name: `024.1 Stream Typewriter ${stamp}`,
      description: 'chatflow streaming typewriter e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'message_1',
          type: 'MESSAGE',
          name: '消息',
          config: {
            content: 'MESSAGE says {{start.sys.query}}',
            outputVariable: 'content',
            streamOutput: 'enabled',
            ui: { position: { x: 460, y: 180 } },
          },
        },
        {
          nodeKey: 'end',
          type: 'END',
          name: '结束',
          config: {
            outputVariable: 'final',
            output: 'END says {{message_1.content}}',
            ui: { position: { x: 820, y: 180 } },
          },
        },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'message_1', condition: null },
        { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create chatflow')

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '对话试运行', exact: true }).click()
  const panel = page.getByTestId('test-run-panel')
  await panel.getByPlaceholder('输入消息').fill('Ada')
  await panel.getByRole('button', { name: '发送消息', exact: true }).click()

  const assistant = panel.getByTestId('chatflow-assistant-message')
  await assistant.waitFor({ state: 'visible', timeout: 12000 })
  await panel.getByTestId('chatflow-typewriter-message').waitFor({ state: 'visible', timeout: 12000 })
  const assistantText = await assistant.innerText()
  assert(assistantText.includes('END says MESSAGE says Ada'), `Expected accumulated typewriter final content, got: ${assistantText}`)

  await page.getByRole('button', { name: '调试工具', exact: true }).click()
  const dock = page.getByTestId('workflow-debug-dock')
  const streamPreview = dock.getByTestId('chatflow-debug-stream-preview')
  await streamPreview.waitFor({ state: 'visible', timeout: 8000 })
  const previewText = await streamPreview.innerText()
  assert(previewText.includes('流式输出'), `Expected stream preview title, got: ${previewText}`)
  assert(previewText.includes('END says MESSAGE says Ada'), `Expected stream preview content, got: ${previewText}`)
  assert(previewText.includes('chunks'), `Expected stream chunk count, got: ${previewText}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS chatflow stream typewriter e2e chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
