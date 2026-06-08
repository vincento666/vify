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
    data: { name: `025.9 Tool MCP ${stamp}`, endpoint: 'mock://tools', description: 'resource panel e2e' },
  }), 'create mcp')
  const toolResourceId = `mcp:${mcp.id}:lookup_order`

  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `025.9 Resource Node Panels ${stamp}`,
      description: 'resource panel alignment e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 80, y: 240 } } } },
        { nodeKey: 'tool_1', type: 'TOOL_CALL', name: '工具调用', config: { resourceId: toolResourceId, resourceType: 'MCP_TOOL', toolName: 'lookup_order', serverIds: [mcp.id], inputMappings: [{ name: 'orderId', valueMode: 'reference', value: '{{start.USER_INPUT}}', required: true }], outputParameters: [{ name: 'result', type: 'string' }, { name: 'success', type: 'boolean' }, { name: 'evidence', type: 'object' }], outputVariable: 'toolResult', ui: { position: { x: 360, y: 80 } } } },
        { nodeKey: 'api_1', type: 'API_CALL', name: 'API 调用', config: { resourceId: 'api-tool:demo', inputMappings: [{ name: 'query', valueMode: 'reference', value: '{{start.USER_INPUT}}' }], endpoint: 'http://example.test', method: 'GET', outputVariable: 'apiResult', ui: { position: { x: 360, y: 240 } } } },
        { nodeKey: 'knowledge_1', type: 'KNOWLEDGE', name: '知识库', config: { resourceId: 'knowledge:demo', knowledgeBaseId: 'legacy-demo', query: '{{start.USER_INPUT}}', topK: 3, outputVariable: 'documents', ui: { position: { x: 360, y: 400 } } } },
        { nodeKey: 'subflow_1', type: 'EXECUTE_WORKFLOW', name: '工作流', config: { resourceId: 'workflow:demo', targetWorkflowId: 'legacy-demo', inputMappings: [{ name: 'ticket', valueMode: 'reference', value: '{{start.USER_INPUT}}' }], outputVariable: 'child', ui: { position: { x: 720, y: 160 } } } },
        { nodeKey: 'agent_1', type: 'AGENT_CALL', name: '智能体', config: { resourceId: 'agent:demo', targetAgentId: 'legacy-demo', messageTemplate: '{{start.USER_INPUT}}', inputMappings: [{ name: 'message', valueMode: 'reference', value: '{{start.USER_INPUT}}' }], outputVariable: 'agentAnswer', ui: { position: { x: 720, y: 360 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{tool_1.result}}', ui: { position: { x: 1080, y: 240 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'tool_1', condition: null },
        { sourceNodeKey: 'tool_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create resource panel workflow')

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  const panel = page.locator('[data-testid="node-config-panel"]')

  async function openNode(selector) {
    if (await panel.isVisible()) {
      await panel.getByRole('button', { name: '关闭配置' }).click()
      await panel.waitFor({ state: 'hidden', timeout: 5000 })
    }
    await page.locator(selector).click()
    await panel.waitFor({ state: 'visible', timeout: 5000 })
    return panel.innerText()
  }

  let text = await openNode('.coze-node.node-tool_call')
  assert(text.includes('工具'), 'Expected tool section')
  assert(text.includes('参数映射'), 'Expected tool schema mapping section')
  assert(!text.includes('参数值模式'), 'Schema mapping must not expose reference/literal mode selector')
  assert(!text.includes('高级/兼容配置'), 'Tool panel must not expose advanced compatibility section')
  assert(!text.includes('MCP Server IDs'), 'Tool panel must not expose legacy MCP server ids')
  assert(await panel.locator('[data-testid="resource-adapter-badge"]').count() === 1, 'Expected adapter badge')
  assert(await panel.locator('[data-testid="schema-input-mapping-row"]').count() >= 1, 'Expected schema mapping rows')
  assert(await panel.locator('[data-testid="schema-input-variable-chip"]').count() >= 1, 'Expected schema mapping reference to render as a variable chip')
  const schemaRow = panel.locator('[data-testid="schema-input-mapping-row"]').first()
  await schemaRow.locator('[data-testid="schema-input-variable-chip"]').click()
  const schemaPicker = schemaRow.locator('[data-testid="schema-input-variable-picker"]')
  await schemaPicker.waitFor({ state: 'visible', timeout: 5000 })
  assert(await schemaPicker.locator('.variable-picker-columns').count() === 0, 'Schema mapping picker must not render the old two-column selector')
  assert(await schemaPicker.locator('.coze-variable-source-item .variable-source-icon, .coze-variable-source-item svg').count() === 0, 'Schema mapping picker should not render source icons or SVG chevrons')
  assert(await schemaPicker.locator('[data-testid="variable-source-arrow"]').count() >= 1, 'Schema mapping picker should mark expandable source rows with a simple arrow')
  assert(await schemaPicker.locator('.coze-variable-source-item small, .coze-variable-source-item em').count() === 0, 'Schema mapping picker should not render source subtitles or counts')
  assert(await page.locator('[data-testid="schema-input-variable-flyout"]').count() === 0, 'Schema mapping flyout should wait for source hover/click')
  const schemaSource = schemaPicker.locator('[data-testid="schema-input-variable-source-item"]', { hasText: '开始' })
  await schemaSource.hover()
  const schemaFlyout = page.locator('[data-testid="schema-input-variable-flyout"]')
  await schemaFlyout.waitFor({ state: 'visible', timeout: 5000 })
  assert((await schemaFlyout.getAttribute('data-placement')) === 'left', 'Schema mapping flyout should adapt left near the config panel edge')
  assert(await schemaFlyout.locator('.variable-item-header, .variable-option-main small, .variable-source-icon, svg').count() === 0, 'Schema mapping flyout should only render variable names and type tags')
  await schemaFlyout.locator('[data-testid="schema-input-variable-option"]', { hasText: 'USER_INPUT' }).click()
  assert(await panel.locator('[data-testid="legacy-resource-debug"]').count() === 0, 'Expected legacy resource debug data to be hidden')

  text = await openNode('.coze-node.node-api_call')
  assert(text.includes('API Resource'), 'Expected API Resource selector section')
  assert(text.includes('参数映射'), 'Expected API schema mapping section')
  assert(!text.includes('参数值模式'), 'API schema mapping must not expose reference/literal mode selector')
  assert(await panel.locator('[data-testid="schema-input-mapping-editor"]').count() === 1, 'Expected API mapping editor')

  text = await openNode('.coze-node.node-knowledge')
  assert(text.includes('知识库'), 'Expected Knowledge resource section')
  assert(text.includes('检索问题'), 'Expected Knowledge query field')
  assert(!text.includes('高级/兼容配置'), 'Knowledge panel must not expose advanced compatibility section')
  assert(!text.includes('知识库 ID'), 'Knowledge panel must not expose legacy knowledgeBaseId')

  text = await openNode('.coze-node.node-execute_workflow')
  assert(text.includes('工作流'), 'Expected subworkflow selector section')
  assert(text.includes('参数映射'), 'Expected subworkflow mapping section')
  assert(!text.includes('高级/兼容配置'), 'Subworkflow panel must not expose advanced compatibility section')
  assert(!text.includes('目标工作流 ID'), 'Subworkflow panel must not expose legacy targetWorkflowId')

  text = await openNode('.coze-node.node-agent_call')
  assert(text.includes('智能体'), 'Expected agent selector section')
  assert(text.includes('消息模板'), 'Expected agent message template')
  assert(await panel.locator('[data-testid="schema-input-mapping-editor"]').count() === 1, 'Expected agent mapping editor')
  assert(!text.includes('高级/兼容配置'), 'Agent panel must not expose advanced compatibility section')
  assert(!text.includes('目标智能体 ID'), 'Agent panel must not expose legacy targetAgentId')

  const run = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
    data: { input: { USER_INPUT: 'A-100' } },
  }), 'run tool mapped workflow')
  assert(run.status === 'SUCCEEDED', `Expected workflow run success, got ${run.status}`)
  assert(JSON.stringify(run.output).includes('A-100'), `Expected tool output to include mapped order id, got ${JSON.stringify(run.output)}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS workflow resource node panels e2e workflow=${workflow.id}`)
} finally {
  await browser.close()
}
