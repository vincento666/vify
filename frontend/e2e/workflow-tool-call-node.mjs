import { chromium } from 'playwright'
import { waitForRuntimeResult } from './runtime-run-helpers.mjs'

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
  const mcp = await unwrap(await page.request.post(`${baseUrl}/api/v1/mcp-servers`, {
    data: { name: `017.2 Tool MCP ${stamp}`, endpoint: 'mock://tools', description: 'tool call e2e' },
  }), 'create mcp')

  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `017.2 Tool Call Workflow ${stamp}`,
      description: 'tool call node e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['orderId'], ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'tool_call_1',
          type: 'TOOL_CALL',
          name: '工具调用',
          config: {
            resourceType: 'MCP_TOOL',
            resourceId: `mcp:${mcp.id}:lookup_order`,
            serverIds: [mcp.id],
            toolName: 'lookup_order',
            inputMappings: [
              { name: 'orderId', valueMode: 'reference', value: '{{start.orderId}}', required: true },
            ],
            outputParameters: [
              { name: 'result', type: 'string' },
              { name: 'success', type: 'boolean' },
              { name: 'evidence', type: 'object' },
            ],
            ui: { position: { x: 500, y: 180 } },
          },
        },
        {
          nodeKey: 'end',
          type: 'END',
          name: '结束',
          config: { outputVariable: 'final', output: '{{tool_call_1.result}}', ui: { position: { x: 880, y: 180 } } },
        },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'tool_call_1', condition: null },
        { sourceNodeKey: 'tool_call_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create workflow')

  const started = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
    data: { input: { orderId: 'A-300' } },
  }), 'run workflow')
  const run = await waitForRuntimeResult(page, baseUrl, started, 'tool call workflow')
  assert(run.status === 'SUCCEEDED', 'Expected full workflow success')
  assert(run.output.final === 'Order A-300 status: SHIPPED', 'Expected TOOL_CALL output to feed END node')

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.getByLabel('添加节点').click()
  const palette = page.locator('[data-testid="bottom-node-palette"]')
  await palette.waitFor({ state: 'visible', timeout: 10000 })
  assert((await palette.innerText()).includes('插件'), 'Expected plugin entry visible in node palette')
  await page.getByLabel('添加节点').click()

  const toolNode = page.locator('.coze-node.node-tool_call')
  await toolNode.waitFor({ state: 'visible', timeout: 10000 })
  await toolNode.click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  const panelText = await panel.innerText()
  assert(panelText.includes('工具'), 'Expected tool selector section')
  assert(panelText.includes('参数映射'), 'Expected schema mapping config section')
  assert(panelText.includes('错误行为'), 'Expected error behavior config field')
  assert(!panelText.includes('资源 ID'), 'Tool panel should hide raw resource id field')
  assert(!panelText.includes('输入映射'), 'Tool panel should hide legacy input mapping field')
  assert(await panel.locator('[data-testid="tool-call-resource-select"]').count() === 1, 'Expected resource selector control')
  assert(await panel.locator('[data-testid="resource-adapter-badge"]').count() === 1, 'Expected resource adapter badge')
  assert(await panel.locator('[data-testid="schema-input-mapping-row"]').count() >= 1, 'Expected schema mapping rows')

  await panel.getByRole('button', { name: '试运行当前节点', exact: true }).click()
  const drawer = page.locator('[data-testid="node-test-drawer"]')
  await drawer.waitFor({ state: 'visible', timeout: 10000 })
  await drawer.locator('.node-test-input-row', { hasText: 'orderId' }).locator('input').fill('A-301')
  await drawer.getByRole('button', { name: '运行', exact: true }).click()
  await drawer.locator('.node-test-status.success').waitFor({ state: 'visible', timeout: 10000 })
  const drawerText = await drawer.innerText()
  assert(drawerText.includes('Order A-301 status: SHIPPED'), 'Expected selected node tool output')
  assert(drawerText.includes('evidence'), 'Expected tool call evidence in selected-node result')
  assert(drawerText.includes('lookup_order'), 'Expected tool name in selected-node evidence')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS workflow tool call node e2e workflow=${workflow.id}`)
} finally {
  await browser.close()
}
