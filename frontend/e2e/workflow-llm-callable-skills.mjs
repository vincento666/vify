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
  const mcp = await unwrap(await page.request.post(`${baseUrl}/api/v1/mcp-servers`, {
    data: { name: `017.3 LLM Skill MCP ${stamp}`, endpoint: 'mock://tools', description: 'llm callable skill e2e' },
  }), 'create mcp')

  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `017.3 LLM Callable Skill ${stamp}`,
      description: 'live LLM callable skill e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['orderId'], ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'llm_1',
          type: 'LLM',
          name: '大模型',
          config: {
            prompt: 'Use the lookup_order tool to look up order {{start.orderId}}. Reply with the order status after the tool result.',
            outputVariable: 'answer',
            temperature: 0,
            maxTokens: 160,
            toolChoiceMode: 'required',
            maxToolRounds: 1,
            toolResultMode: 'separate',
            resources: [
              {
                type: 'MCP_TOOL',
                resourceType: 'MCP_TOOL',
                resourceId: `mcp:${mcp.id}:lookup_order`,
                serverIds: [mcp.id],
                toolName: 'lookup_order',
                enabled: true,
              },
            ],
            outputParameters: [
              { name: 'answer', type: 'string' },
              { name: 'toolCalls', type: 'array' },
            ],
            ui: { position: { x: 500, y: 180 } },
          },
        },
        {
          nodeKey: 'end',
          type: 'END',
          name: '结束',
          config: { outputVariable: 'final', output: '{{llm_1.answer}}', ui: { position: { x: 900, y: 180 } } },
        },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
        { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create workflow')

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-llm').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.coze-node.node-llm').click()

  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  const panelText = await panel.innerText()
  assert(panelText.includes('技能'), 'Expected LLM skill section')
  assert(panelText.includes('MCP 工具'), 'Expected selected MCP skill resource card')
  assert(!panelText.includes('工具选择'), 'Tool choice policy should not render as a basic form field')
  assert(!panelText.includes('最大调用轮次'), 'Max tool rounds should not render as a basic form field')
  assert(!panelText.includes('工具结果'), 'Tool result mode should not render as a basic form field')

  const persisted = await unwrap(await page.request.get(`${baseUrl}/api/v1/workflows/${workflow.id}`), 'get workflow')
  const llmNode = persisted.nodes.find((node) => node.nodeKey === 'llm_1')
  assert(llmNode, 'Expected persisted LLM node')
  assert(llmNode.config.toolChoiceMode === 'required', 'Expected callable skill policy to persist in config')
  assert(llmNode.config.maxToolRounds === 1, 'Expected max tool rounds to persist in config')
  assert(llmNode.config.toolResultMode === 'separate', 'Expected tool result mode to persist in config')
  assert(
    Array.isArray(llmNode.config.resources) && String(llmNode.config.resources[0]?.resourceId || '').includes('lookup_order'),
    'Expected selected callable MCP tool resource to persist in config',
  )

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS workflow LLM callable skills e2e workflow=${workflow.id}`)
} finally {
  await browser.close()
}
