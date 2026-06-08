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
  const enabledMcp = await unwrap(await page.request.post(`${baseUrl}/api/v1/mcp-servers`, {
    data: { name: `017.1 Enabled MCP ${stamp}`, endpoint: 'mock://tools', description: 'registry e2e' },
  }), 'create enabled mcp')
  const disabledMcp = await unwrap(await page.request.post(`${baseUrl}/api/v1/mcp-servers`, {
    data: { name: `017.1 Disabled MCP ${stamp}`, endpoint: 'mock://tools', description: 'registry e2e' },
  }), 'create disabled mcp')
  await unwrap(await page.request.put(`${baseUrl}/api/v1/mcp-servers/${disabledMcp.id}`, {
    data: { enabled: 0 },
  }), 'disable mcp')
  await unwrap(await page.request.post(`${baseUrl}/api/v1/mcp-servers`, {
    data: { name: `017.1 Missing Credential MCP ${stamp}`, endpoint: 'mock://tools?credential=missing', description: 'registry e2e' },
  }), 'create missing credential mcp')

  const registry = await unwrap(await page.request.get(`${baseUrl}/api/v1/workflow-resources`, {
    params: { flowType: 'WORKFLOW' },
  }), 'list workflow resources')
  assert(registry.list.some((resource) => resource.resourceId === `mcp:${enabledMcp.id}:lookup_order` && resource.enabled), 'Expected enabled lookup_order resource')
  assert(registry.list.some((resource) => resource.resourceId === `mcp:${disabledMcp.id}` && resource.runtimeStatus === 'DISABLED'), 'Expected disabled MCP resource')

  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `017.1 Resource Registry Canvas ${stamp}`,
      description: 'registry picker e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 160 } } } },
        { nodeKey: 'llm_1', type: 'LLM', name: '大模型', config: { prompt: 'hello', outputVariable: 'answer', ui: { position: { x: 460, y: 160 } } } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{llm_1.answer}}', ui: { position: { x: 820, y: 160 } } } },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
        { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create registry workflow')

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-llm').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.coze-node.node-llm').click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 10000 })
  const resourceSection = panel.locator('[data-testid="llm-resource-section"]')
  await resourceSection.getByRole('button', { name: '添加资源', exact: true }).click()
  const skillTabs = resourceSection.locator('[data-testid="llm-skill-type-tabs"]')
  await skillTabs.waitFor({ state: 'visible', timeout: 10000 })
  await skillTabs.getByRole('tab', { name: 'MCP 工具', exact: true }).click()
  assert(await resourceSection.locator('[data-testid="workflow-resource-registry"]').count() === 0, 'Expected old mixed resource registry panel to stay absent')

  const search = resourceSection.getByPlaceholder('搜索技能')
  const resourceList = resourceSection.locator('[data-testid="llm-skill-resource-list"]')
  await search.fill('lookup_order')
  await resourceList.locator('button', { hasText: 'lookup_order' }).first().waitFor({ state: 'visible', timeout: 10000 })
  const enabledButton = resourceList.locator('button', { hasText: 'lookup_order' }).first()
  assert(await enabledButton.isEnabled(), 'Expected enabled MCP tool selectable in the tabbed skill picker')
  assert((await enabledButton.innerText()).includes('可用'), 'Expected enabled status visible in the tabbed skill picker')

  await search.fill(`Disabled MCP ${stamp}`)
  const disabledButton = resourceList.locator('button', { hasText: `Disabled MCP ${stamp}` }).first()
  await disabledButton.waitFor({ state: 'visible', timeout: 10000 })
  assert(!(await disabledButton.isEnabled()), 'Expected disabled MCP resource to be non-selectable')
  assert((await disabledButton.innerText()).includes('已停用'), 'Expected disabled status visible in the tabbed skill picker')

  await search.fill(`Missing Credential MCP ${stamp}`)
  const missingCredentialButton = resourceList.locator('button', { hasText: `Missing Credential MCP ${stamp}` }).first()
  await missingCredentialButton.waitFor({ state: 'visible', timeout: 10000 })
  assert(!(await missingCredentialButton.isEnabled()), 'Expected missing-credential resource to be non-selectable')
  assert((await missingCredentialButton.innerText()).includes('缺少凭证'), 'Expected missing credential status visible in the tabbed skill picker')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow resource registry e2e')
} finally {
  await browser.close()
}
