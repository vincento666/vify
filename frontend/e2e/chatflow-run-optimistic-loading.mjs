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
      name: `Chatflow optimistic run ${stamp}`,
      description: 'chatflow optimistic loading e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 120, y: 180 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: 'echo {{start.sys.query}}', ui: { position: { x: 520, y: 180 } } } },
      ],
      edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
    },
  }), 'create chatflow')

  let runRequestSeen = false
  await page.route(`**/api/v1/chatflows/${chatflow.id}/runs-legacy`, async (route) => {
    runRequestSeen = true
    await new Promise((resolve) => setTimeout(resolve, 1200))
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 200,
        message: 'OK',
        data: {
          runId: 987001,
          status: 'SUCCEEDED',
          output: { output: 'echo delayed hello' },
          streamEvents: [],
        },
      }),
    })
  })

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '对话试运行', exact: true }).click()
  const panel = page.getByTestId('test-run-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })

  const input = panel.getByTestId('chatflow-run-message-input')
  await input.fill('delayed hello')
  await panel.getByRole('button', { name: '发送消息', exact: true }).click()

  assert(await input.inputValue() === '', 'Message input should clear immediately after send')
  await panel.getByTestId('chatflow-user-message').waitFor({ state: 'visible', timeout: 1000 })
  assert((await panel.getByTestId('chatflow-user-message').innerText()).includes('delayed hello'), 'User message should render immediately')
  await panel.getByTestId('chatflow-assistant-loading').waitFor({ state: 'visible', timeout: 1000 })
  const runRequestDeadline = Date.now() + 3000
  while (!runRequestSeen && Date.now() < runRequestDeadline) {
    await page.waitForTimeout(50)
  }
  assert(runRequestSeen, 'Run request should be in flight while loading bubble is visible')
  assert(await panel.getByTestId('chatflow-assistant-loading').count() > 0, 'Loading bubble should remain visible during the delayed run request')
  const nodeRunStatus = page.getByTestId('node-run-status').first()
  await nodeRunStatus.waitFor({ state: 'visible', timeout: 1000 })
  assert((await nodeRunStatus.innerText()).includes('运行中'), 'Canvas node should show running state while run request is pending')

  const assistantMessage = panel.getByTestId('chatflow-assistant-message')
  const finalTextDeadline = Date.now() + 4000
  let assistantText = ''
  while (!assistantText.includes('echo delayed hello') && Date.now() < finalTextDeadline) {
    assistantText = await assistantMessage.innerText()
    await page.waitForTimeout(50)
  }
  assert(assistantText.includes('echo delayed hello'), `Assistant bubble should be replaced with final output, got: ${assistantText}`)
  assert(await panel.getByTestId('chatflow-assistant-loading').count() === 0, 'Loading bubble should disappear after run completes')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS chatflow optimistic loading e2e chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
