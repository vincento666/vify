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
  throw new Error('No enabled model found for Agent tool policy e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const modelConfigId = await findEnabledModel(page)
  const server = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/mcp-servers`, {
      data: {
        name: `Tool Policy MCP ${Date.now()}`,
        endpoint: 'mock://tools',
        description: 'tool policy e2e',
      },
    }),
    'create mcp server',
  )
  const agent = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `Tool Policy Agent ${Date.now()}`,
        systemPrompt:
          'You have a function tool named lookup_order. For any order status question, you must call lookup_order with the order id. Do not answer without calling lookup_order.',
        modelConfigId,
        temperature: 0.2,
        maxTokens: 512,
        maxContextTurns: 4,
        toolIds: [server.id],
        toolPolicies: {
          lookup_order: {
            enabled: false,
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

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench`, { waitUntil: 'load' })
  const panel = page.getByTestId('agent-tool-policy-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.locator('summary').click()
  await panel.getByText('lookup_order').waitFor({ state: 'visible', timeout: 5000 })
  const policyLayout = await panel.evaluate((element) => {
    const list = element.querySelector('.tool-policy-list')
    return {
      clientWidth: list?.clientWidth ?? 0,
      scrollWidth: list?.scrollWidth ?? 0,
      text: element.textContent ?? '',
    }
  })
  assert(policyLayout.scrollWidth <= policyLayout.clientWidth + 2, `tool policy panel should not overflow: ${JSON.stringify(policyLayout)}`)
  assert(!policyLayout.text.includes('Fake MCP tool metadata'), 'tool policy panel must not show fake metadata copy')
  assert(policyLayout.text.includes('运行时实际约束'), 'tool policy panel should explain the policy is runtime-effective')

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
  const content = turn.assistantMessage.content
  assert(!content.includes('Order A-100'), 'disabled policy must not return real MCP tool result')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent workbench tool policy e2e')
} finally {
  await browser.close()
}
