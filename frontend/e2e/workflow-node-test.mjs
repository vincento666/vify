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
  let fallbackModelId = null
  for (let pageNo = 1; pageNo <= 20; pageNo += 1) {
    const providers = await unwrap(
      await page.request.get(`${baseUrl}/api/v1/providers?page=${pageNo}&pageSize=100`),
      'list providers',
    )
    for (const provider of providers.list ?? []) {
      if (!provider.enabled) continue
      for (const model of provider.models ?? []) {
        if (!model.enabled) continue
        if (String(provider.baseUrl || '').startsWith('mock://success')) return model.id
        fallbackModelId ??= model.id
      }
    }
    if ((providers.list ?? []).length === 0 || pageNo * 100 >= providers.total) break
  }
  if (fallbackModelId) return fallbackModelId
  throw new Error('No enabled model found for workflow selected-node test e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Workflow Node Test ${Date.now()}`

try {
  const modelConfigId = await findEnabledModel(page)
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name,
        description: 'selected node test evidence',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 160, y: 180 } } } },
          {
            nodeKey: 'llm',
            type: 'LLM',
            name: '大模型',
            config: {
              modelConfigId,
              prompt: '请用一句话回应节点试运行输入：{{start.userMessage}}',
              outputVariable: 'answer',
              ui: { position: { x: 520, y: 160 } },
            },
          },
          {
            nodeKey: 'end',
            type: 'END',
            name: '结束',
            config: { outputVariable: 'answer', output: 'DOWNSTREAM {{llm.answer}}', ui: { position: { x: 860, y: 180 } } },
          },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm', condition: null },
          { sourceNodeKey: 'llm', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create node-test workflow',
  )

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-llm').click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByRole('button', { name: '试运行当前节点', exact: true }).click()

  const drawer = page.locator('[data-testid="node-test-drawer"]')
  await drawer.waitFor({ state: 'visible', timeout: 5000 })
  assert((await drawer.innerText()).includes('试运行输入'), 'Expected selected-node input section')
  await drawer.locator('.node-test-input-row', { hasText: 'userMessage' }).locator('input').fill('节点单独试运行')
  await drawer.getByRole('button', { name: '运行', exact: true }).click()
  await drawer.getByText('SUCCEEDED').waitFor({ state: 'visible', timeout: 30000 })
  const drawerText = await drawer.innerText()
  assert(drawerText.includes('输入'), 'Expected node test to show input')
  assert(drawerText.includes('推理内容'), 'Expected node test to show reasoning content')
  assert(drawerText.includes('技能调用'), 'Expected node test to show skill-call section')
  assert(drawerText.includes('输出'), 'Expected node test to show output')
  assert(!drawerText.includes('DOWNSTREAM'), 'Expected selected-node run not to continue into END node')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow selected-node test e2e')
} finally {
  await browser.close()
}
