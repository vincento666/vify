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
  throw new Error('No enabled model found for Agent memory variable e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const modelConfigId = await findEnabledModel(page)
  const agent = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `Memory Variable Agent ${Date.now()}`,
        systemPrompt: 'When the user asks 请读取变量, reply with the exact runtime context values in the format customer_name=<value>; tier=<value>; last_order=<value>. Do not add any other words.',
        modelConfigId,
        temperature: 0.2,
        maxTokens: 512,
        maxContextTurns: 4,
        toolIds: [],
        variables: [
          {
            name: 'customer_name',
            type: 'string',
            defaultValue: 'Ada',
            required: true,
            description: 'customer name',
          },
          {
            name: 'tier',
            type: 'string',
            defaultValue: 'gold',
            required: false,
            description: 'customer tier',
          },
        ],
        memory: {
          last_order: 'A-100',
        },
      },
    }),
    'create agent',
  )

  await page.goto(`${baseUrl}/agents/${agent.id}/workbench`, { waitUntil: 'load' })
  await page.getByTestId('agent-context-panel').waitFor({ state: 'visible', timeout: 5000 })
  await waitForInputValue(page, 'agent-context-panel', 'customer_name')
  await waitForInputValue(page, 'agent-context-panel', 'Ada')
  await waitForInputValue(page, 'agent-context-panel', 'last_order')

  const overrides = page.getByTestId('agent-preview-variable-overrides')
  const customerOverride = overrides.locator('label').filter({ hasText: 'customer_name' }).getByRole('textbox')
  await customerOverride.fill('Vincent')
  await page.locator('textarea[placeholder="输入预览消息"]').fill('请读取变量。请逐字返回上下文字段。')
  await page.getByRole('button', { name: '发送预览消息' }).click()
  await page.getByText('customer_name=Vincent', { exact: false }).waitFor({ state: 'visible', timeout: 60000 })
  await page.getByText('tier=gold', { exact: false }).waitFor({ state: 'visible', timeout: 60000 })
  await page.getByText('last_order=A-100', { exact: false }).waitFor({ state: 'visible', timeout: 60000 })

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent workbench memory variables e2e')
} finally {
  await browser.close()
}

async function waitForInputValue(page, testId, expectedValue) {
  await page.waitForFunction(
    ([targetTestId, targetValue]) => {
      const panel = document.querySelector(`[data-testid="${targetTestId}"]`)
      return Array.from(panel?.querySelectorAll('input, textarea') ?? []).some(
        (input) => input.value === targetValue,
      )
    },
    [testId, expectedValue],
    { timeout: 5000 },
  )
}
