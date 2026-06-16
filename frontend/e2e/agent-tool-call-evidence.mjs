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
  for (let pageNo = 1; pageNo <= 20; pageNo += 1) {
    const providers = await unwrap(
      await page.request.get(`${baseUrl}/api/v1/providers?page=${pageNo}&pageSize=100`),
      'list providers',
    )
    for (const provider of providers.list ?? []) {
      if (!provider.enabled) continue
      if (String(provider.baseUrl || '').startsWith('mock://')) continue
      for (const model of provider.models ?? []) {
        if (model.enabled) return model.id
      }
    }
    if ((providers.list ?? []).length === 0 || pageNo * 100 >= providers.total) break
  }
  throw new Error('No enabled model found for Agent tool evidence e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const modelConfigId = await findEnabledModel(page)
  const server = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/mcp-servers`, {
      data: {
        name: `Tool Evidence MCP ${Date.now()}`,
        endpoint: 'mock://tools',
        description: 'tool evidence e2e',
      },
    }),
    'create mcp server',
  )
  const agent = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `Tool Evidence Agent ${Date.now()}`,
        systemPrompt:
          'You have a function tool named lookup_order. For any order status question, call lookup_order with the order id before answering.',
        modelConfigId,
        temperature: 0,
        maxTokens: 512,
        maxContextTurns: 4,
        toolIds: [server.id],
        toolPolicies: {
          lookup_order: {
            enabled: true,
            callMode: 'auto',
            argumentPresets: {},
            timeoutMs: 30000,
            failureBehavior: 'return_error',
          },
        },
      },
    }),
    'create agent',
  )

  const session = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chat/sessions`, { data: { agentId: agent.id } }),
    'create chat session',
  )
  const turn = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chat/sessions/${session.id}/messages`, {
      data: { content: 'Where is order A-100? Use lookup_order.', stream: false },
    }),
    'send chat message',
  )
  const toolCalls = turn.assistantMessage.toolCalls ?? []
  assert(toolCalls.length === 1, `expected one tool call, got ${JSON.stringify(toolCalls)}`)
  assert(toolCalls[0].status === 'success', `expected success tool evidence, got ${JSON.stringify(toolCalls[0])}`)
  assert(toolCalls[0].toolName === 'lookup_order', `expected lookup_order, got ${JSON.stringify(toolCalls[0])}`)
  assert(String(toolCalls[0].argumentsSummary).includes('A-100'), `arguments summary should include order id: ${JSON.stringify(toolCalls[0])}`)
  assert(String(toolCalls[0].contentSummary).includes('SHIPPED'), `content summary should include tool result: ${JSON.stringify(toolCalls[0])}`)

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench?previewRunId=${session.id}&debug=1`, { waitUntil: 'load' })
  const debugPanel = page.getByTestId('agent-debug-detail-panel')
  await debugPanel.getByText('调试详情').waitFor({ state: 'visible', timeout: 5000 })
  await debugPanel.getByText('调用工具 lookup_order').waitFor({ state: 'visible', timeout: 5000 })
  await debugPanel.getByText('success').waitFor({ state: 'visible', timeout: 5000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }
  console.log(`PASS agent tool call evidence e2e agent=${agent.id} session=${session.id}`)
} finally {
  await browser.close()
}
