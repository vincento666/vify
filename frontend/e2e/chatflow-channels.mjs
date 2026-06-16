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
      name: `019.2 Channel E2E ${stamp}`,
      description: 'channel adapter e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'end',
          type: 'END',
          name: '结束',
          config: {
            outputVariable: 'final',
            output: '{{sys.query}} via {{sys.channel}}/{{sys.channel_id}}/{{sys.user_id}} files={{sys.files}}',
            ui: { position: { x: 640, y: 180 } },
          },
        },
      ],
      edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
    },
  }), 'create chatflow')

  await unwrap(await page.request.put(`${baseUrl}/api/v1/chatflows/${chatflow.id}/channels/api`, {
    data: { enabled: true, displayName: 'Production API', config: { channelId: 'api-prod' } },
  }), 'update api channel')

  const apiResult = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/channels/api/test`, {
    data: {
      message: 'hello channel',
      conversationId: `conv-api-${stamp}`,
      userId: 'user-api',
      channelId: 'api-request',
      files: [{ name: 'invoice.txt' }],
    },
  }), 'api channel test')
  assert(apiResult.run.status === 'SUCCEEDED', 'Expected API channel run succeeded')
  assert(apiResult.runtimeInput['sys.channel'] === 'api', 'Expected API sys.channel')
  assert(apiResult.runtimeInput['sys.channel_id'] === 'api-request', 'Expected API channel id')
  assert(apiResult.run.output.final.includes('hello channel via api/api-request/user-api'), 'Expected API output to include identity')

  const webResult = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/channels/web/test`, {
    data: { message: 'hello web', userId: 'web-user' },
  }), 'web channel test')
  assert(webResult.run.status === 'SUCCEEDED', 'Expected Web channel run succeeded')
  assert(webResult.runtimeInput['sys.channel'] === 'web', 'Expected Web sys.channel')
  assert(webResult.run.output.final.includes('hello web via web/web-preview/web-user'), 'Expected Web output to include identity')

  const directResult = await unwrap(await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
    data: {
      input: {
        message: 'hello direct api',
        conversationId: `conv-direct-${stamp}`,
        userId: 'direct-user',
        channelId: 'direct-api-request',
      },
    },
  }), 'direct chatflow run')
  assert(directResult.status === 'SUCCEEDED', 'Expected direct chatflow run succeeded')
  assert(
    directResult.output.final.includes('hello direct api via api/direct-api-request/direct-user'),
    `Expected direct output to include normalized identity, got ${JSON.stringify(directResult.output)}`,
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '开放', exact: true }).click()
  const shells = page.getByTestId('chatflow-channel-shells')
  await shells.getByText('Production API', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await shells.getByText('Web Chat', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await shells.getByText('Feishu', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  await shells.getByText('缺少 webhook 验签和凭据配置', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })
  assert(await shells.getByText('同步 / 流式 / 文件', { exact: true }).count() >= 2, 'Expected API/Web delivery capabilities')
  assert(await shells.getByText('sys.query · sys.channel · sys.channel_id · sys.conversation_id · sys.user_id · sys.files · channel.metadata', { exact: true }).count() >= 1, 'Expected normalized channel input fields')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS chatflow channels e2e chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
