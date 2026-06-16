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
        if (model.enabled) return { id: model.id, name: model.name }
      }
    }
    if ((providers.list ?? []).length === 0 || pageNo * 100 >= providers.total) break
  }
  throw new Error('No enabled model found for Agent workbench core e2e')
}

async function chooseModel(page, modelName) {
  await page.locator('.field-row', { hasText: '模型' }).locator('.el-select').click()
  const option = page.locator('.el-select-dropdown__item', { hasText: modelName })
  await option.first().waitFor({ state: 'visible', timeout: 10000 })
  await option.first().click()
}

async function fillHeaderName(page, name) {
  await page.getByRole('button', { name: '修改 Agent 名称' }).click()
  await page.getByPlaceholder('请输入 Agent 名称').fill(name)
  await page.getByPlaceholder('请输入 Agent 名称').press('Enter')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const model = await findEnabledModel(page)
  const agentName = `Workbench Core Agent ${Date.now()}`

  await page.goto(`${baseUrl}/agents/new`, { waitUntil: 'networkidle' })
  await page.getByTestId('agent-workbench-shell').waitFor({ state: 'visible', timeout: 5000 })
  assert(await page.getByRole('button', { name: '保存配置', exact: true }).isDisabled(), 'Expected save disabled before valid input')
  await fillHeaderName(page, agentName)
  await chooseModel(page, model.name)
  await page.getByPlaceholder('定义 Agent 的角色、行为和约束...').fill('You are an e2e workbench agent.')
  await page.getByRole('button', { name: '保存配置', exact: true }).click()
  await page.waitForURL(/\/agents\/\d+\/workbench/, { timeout: 10000 })
  const agentId = Number(page.url().match(/\/agents\/(\d+)\/workbench/)?.[1])
  assert(agentId > 0, 'Expected created Agent id in URL')

  const created = await unwrap(await page.request.get(`${baseUrl}/api/v1/agents/${agentId}`), 'get created agent')
  assert(created.name === agentName, `Expected created name, got ${created.name}`)
  assert(created.modelConfigId === model.id, `Expected model ${model.id}, got ${created.modelConfigId}`)
  assert(created.systemPrompt === 'You are an e2e workbench agent.', 'Expected system prompt to persist')

  const editedName = `${agentName} Edited`
  await fillHeaderName(page, editedName)
  await page.getByPlaceholder('定义 Agent 的角色、行为和约束...').fill('Updated workbench instructions.')
  assert(!(await page.getByRole('button', { name: '保存配置', exact: true }).isDisabled()), 'Expected save enabled after edit')
  const updateResponse = page.waitForResponse((response) =>
    response.url().includes(`/api/v1/agents/${agentId}`)
      && response.request().method() === 'PUT',
  )
  await page.getByRole('button', { name: '保存配置', exact: true }).click()
  await updateResponse
  await page.getByText('已保存', { exact: true }).waitFor({ state: 'visible', timeout: 10000 })

  const updated = await unwrap(await page.request.get(`${baseUrl}/api/v1/agents/${agentId}`), 'get updated agent')
  assert(updated.name === editedName, `Expected updated name, got ${updated.name}`)
  assert(updated.systemPrompt === 'Updated workbench instructions.', 'Expected updated prompt to persist')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS agent workbench core config e2e')
} finally {
  await browser.close()
}
