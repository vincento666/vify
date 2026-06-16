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

async function findEnabledModel(page) {
  const providers = await unwrap(await page.request.get(`${baseUrl}/api/v1/providers?page=1&pageSize=100`), 'list providers')
  for (const provider of providers.list ?? []) {
    if (!provider.enabled) continue
    for (const model of provider.models ?? []) {
      if (model.enabled) return model.id
    }
  }
  throw new Error('No enabled model found for Agent runtime e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const suffix = Date.now()
  const modelConfigId = await findEnabledModel(page)
  const mcp = await unwrap(await page.request.post(`${baseUrl}/api/v1/mcp-servers`, {
    data: { name: `Runtime MCP ${suffix}`, endpoint: `http://127.0.0.1:${13000 + (suffix % 1000)}/mcp`, description: 'runtime e2e' },
  }), 'create mcp')
  const kb = await unwrap(await page.request.post(`${baseUrl}/api/v1/knowledge-bases`, {
    data: { name: `Runtime KB ${suffix}`, description: 'runtime e2e' },
  }), 'create kb')
  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `Runtime Workflow ${suffix}`,
      description: 'runtime e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'] } },
        { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{start.USER_INPUT}}' } },
      ],
      edges: [{ sourceNodeKey: 'start', targetNodeKey: 'end', condition: null }],
    },
  }), 'create workflow')
  const agent = await unwrap(await page.request.post(`${baseUrl}/api/v1/agents`, {
    data: {
      name: `Runtime Agent ${suffix}`,
      description: 'runtime e2e',
      systemPrompt: 'Runtime e2e.',
      modelConfigId,
      temperature: 0.2,
      maxTokens: 256,
      maxContextTurns: 4,
      toolIds: [mcp.id],
      knowledgeBaseId: kb.id,
      workflowId: workflow.id,
    },
  }), 'create agent')

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench`, { waitUntil: 'networkidle' })
  const runtime = page.getByTestId('agent-runtime-summary')
  await runtime.waitFor({ state: 'visible', timeout: 5000 })
  const text = await runtime.innerText()
  assert(text.includes('运行优先级提示'), 'Expected priority notice title')
  assert(!text.includes('LLM'), 'Expected runtime notice not to restate default LLM streaming mode')
  assert(text.includes('已绑定知识库，但工作流优先'), 'Expected knowledge precedence warning')
  assert(text.includes('已绑定 MCP 工具，但工作流模式优先'), 'Expected tool precedence warning')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent runtime mode e2e')
} finally {
  await browser.close()
}
