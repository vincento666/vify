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
  const missingCredentialMcp = await unwrap(await page.request.post(`${baseUrl}/api/v1/mcp-servers`, {
    data: { name: `017.5 Missing Credential ${stamp}`, endpoint: 'mock://tools?credential=missing', description: 'policy e2e' },
  }), 'create missing credential mcp')
  const slowMcp = await unwrap(await page.request.post(`${baseUrl}/api/v1/mcp-servers`, {
    data: { name: `017.5 Slow MCP ${stamp}`, endpoint: 'mock://tools?elapsed=500', description: 'policy e2e' },
  }), 'create slow mcp')

  const registry = await unwrap(await page.request.get(`${baseUrl}/api/v1/workflow-resources`, {
    params: { flowType: 'WORKFLOW' },
  }), 'list workflow resources')
  const missingCredentialResource = registry.list.find((resource) => resource.resourceId === `mcp:${missingCredentialMcp.id}`)
  assert(missingCredentialResource, 'Expected missing credential resource')
  assert(missingCredentialResource.enabled === false, 'Expected missing credential resource disabled')
  assert(missingCredentialResource.disabledReason.includes('credential'), 'Expected disabled reason to mention credential')

  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `017.5 Resource Policy ${stamp}`,
      description: 'resource policy e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['orderId'], ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'tool_call_1',
          type: 'TOOL_CALL',
          name: '工具调用',
          config: {
            resourceType: 'MCP_TOOL',
            resourceId: `mcp:${slowMcp.id}:lookup_order`,
            serverIds: [slowMcp.id],
            toolName: 'lookup_order',
            inputMappings: [
              { name: 'orderId', valueMode: 'reference', value: '{{start.orderId}}', required: true },
            ],
            timeoutMs: 100,
            retryCount: 0,
            errorBehavior: 'continue',
            outputParameters: [
              { name: 'result', type: 'string' },
              { name: 'success', type: 'boolean' },
              { name: 'error', type: 'string' },
              { name: 'evidence', type: 'object' },
            ],
            ui: { position: { x: 500, y: 180 } },
          },
        },
        {
          nodeKey: 'end',
          type: 'END',
          name: '结束',
          config: { outputVariable: 'final', output: 'success={{tool_call_1.success}} error={{tool_call_1.error}}', ui: { position: { x: 880, y: 180 } } },
        },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'tool_call_1', condition: null },
        { sourceNodeKey: 'tool_call_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create policy workflow')

  const run = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
    data: { input: { orderId: 'A-801' } },
  }), 'run policy workflow')
  assert(run.status === 'SUCCEEDED', 'Expected continue policy to keep parent run succeeded')
  assert(run.output.final.includes('success=False'), 'Expected failure success flag in final output')
  assert(run.output.final.includes('timed out'), 'Expected timeout evidence in final output')

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  const toolNode = page.locator('.coze-node.node-tool_call')
  await toolNode.waitFor({ state: 'visible', timeout: 10000 })
  await toolNode.click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  const panelText = await panel.innerText()
  assert(panelText.includes('错误行为'), 'Expected error behavior field')
  assert(panelText.includes('重试次数'), 'Expected retry count field')
  assert(!panelText.includes('超时毫秒'), 'Tool panel should not expose raw timeout field in the basic UI')
  assert(await panel.locator('[data-testid="tool-call-resource-select"]').count() === 1, 'Expected resource selector control')
  assert(await panel.locator('[data-testid="schema-input-mapping-row"]').count() >= 1, 'Expected schema mapping rows')
  await panel.getByRole('button', { name: '试运行当前节点', exact: true }).click()
  const drawer = page.locator('[data-testid="node-test-drawer"]')
  await drawer.waitFor({ state: 'visible', timeout: 10000 })
  await drawer.locator('.node-test-input-row', { hasText: 'orderId' }).locator('input').fill('A-802')
  await drawer.getByRole('button', { name: '运行', exact: true }).click()
  await drawer.locator('.node-test-status.success').waitFor({ state: 'visible', timeout: 10000 })
  const drawerText = await drawer.innerText()
  assert(drawerText.includes('timed out'), 'Expected selected-node timeout error')
  assert(drawerText.includes('FAILED'), 'Expected evidence status failed')
  assert(drawerText.includes('timeoutMs'), 'Expected timeout evidence')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS workflow resource policy e2e workflow=${workflow.id}`)
} finally {
  await browser.close()
}
