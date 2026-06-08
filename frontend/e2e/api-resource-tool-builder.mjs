import http from 'node:http'
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

function startLocalApiServer() {
  const server = http.createServer((request, response) => {
    if (request.url?.startsWith('/text/orders/')) {
      response.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' })
      response.end(`API_REAL: GET ${request.url}`)
      return
    }
    response.writeHead(200, { 'Content-Type': 'application/json' })
    response.end(JSON.stringify({ ok: true, path: request.url, method: request.method }))
  })
  return new Promise((resolve) => {
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      resolve({
        url: `http://127.0.0.1:${address.port}`,
        close: () => new Promise((done) => server.close(done)),
      })
    })
  })
}

const localApi = await startLocalApiServer()
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const stamp = Date.now()
  await page.goto(`${baseUrl}/workflow/api-resources`, { waitUntil: 'networkidle' })

  await page.getByTestId('api-resource-name').fill(`Orders API ${stamp}`)
  await page.getByTestId('api-resource-endpoint').fill(`${localApi.url}/text/orders/{{orderId}}`)
  await page.getByTestId('api-resource-input-schema').fill(
    JSON.stringify({
      type: 'object',
      properties: { orderId: { type: 'string' } },
      required: ['orderId'],
    }),
  )
  await page.getByTestId('api-resource-test-payload').fill(JSON.stringify({ orderId: 'A-210' }))
  await page.getByTestId('api-resource-create').click()
  await page.getByTestId('api-resource-list').getByText(`Orders API ${stamp}`).waitFor({ state: 'visible', timeout: 10000 })

  await page.getByTestId('api-resource-test').click()
  await page.getByTestId('api-resource-test-result').waitFor({ state: 'visible', timeout: 10000 })
  const testResult = await page.getByTestId('api-resource-test-result').innerText()
  assert(testResult.includes('API_REAL: GET /text/orders/A-210'), 'Expected API Resource test-call response')
  assert(!testResult.toLowerCase().includes('secret'), 'Expected sanitized test evidence')

  await page.getByTestId('api-tool-name').fill(`lookup_order_api_${stamp}`)
  await page.getByTestId('api-tool-create').click()
  await page.getByTestId('api-tool-list').getByText(`lookup_order_api_${stamp}`).waitFor({ state: 'visible', timeout: 10000 })

  const tools = await unwrap(await page.request.get(`${baseUrl}/api/v1/tools`, {
    params: { adapterType: 'API_RESOURCE', pageSize: 100 },
  }), 'list API tools')
  const apiTool = tools.list.find((tool) => tool.name === `lookup_order_api_${stamp}`)
  assert(apiTool, 'Expected API Tool created by UI')

  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `API Tool Canvas ${stamp}`,
      description: 'API Resource e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { startVariables: [{ name: 'orderId', type: 'string', required: true }], ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'tool_call_1',
          type: 'TOOL_CALL',
          name: '工具调用',
          config: {
            resourceType: 'MCP_TOOL',
            resourceId: '',
            toolName: '',
            serverIds: [],
            inputMappings: [
              { name: 'orderId', type: 'string', valueMode: 'reference', value: '{{start.orderId}}', required: true },
            ],
            outputParameters: [
              { name: 'result', type: 'string' },
              { name: 'success', type: 'boolean' },
              { name: 'evidence', type: 'object' },
            ],
            ui: { position: { x: 500, y: 180 } },
          },
        },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{tool_call_1.result}}', ui: { position: { x: 880, y: 180 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'tool_call_1', condition: null },
        { sourceNodeKey: 'tool_call_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create workflow')

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-tool_call').click()
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  await panel.getByTestId('tool-call-resource-select').click()
  await page.getByRole('option', { name: new RegExp(`lookup_order_api_${stamp}`) }).click()
  await page.getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForResponse((response) => response.url().includes(`/api/v1/workflows/${workflow.id}`) && response.request().method() === 'PUT')

  const saved = await unwrap(await page.request.get(`${baseUrl}/api/v1/workflows/${workflow.id}`), 'get workflow')
  const toolNode = saved.nodes.find((node) => node.nodeKey === 'tool_call_1')
  assert(toolNode.config.resourceType === 'API_TOOL', `Expected API_TOOL config: ${JSON.stringify(toolNode.config)}`)
  assert(toolNode.config.resourceId === apiTool.resourceId, `Expected selected resource id: ${JSON.stringify(toolNode.config)}`)

  const run = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
    data: { input: { orderId: 'A-211' } },
  }), 'run workflow')
  assert(run.status === 'SUCCEEDED', 'Expected workflow run success')
  assert(run.output.final === 'API_REAL: GET /text/orders/A-211', `Unexpected output: ${JSON.stringify(run.output)}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS api resource tool builder workflow=${workflow.id}`)
} finally {
  await browser.close()
  await localApi.close()
}
