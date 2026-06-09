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
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name: `Variable Aggregation Official ${Date.now()}`,
        description: 'official variable aggregation panel parity',
        nodes: [
          {
            nodeKey: 'start',
            type: 'START',
            name: '开始',
            config: {
              startVariables: [
                { name: 'primary', type: 'string', required: true },
                { name: 'fallback', type: 'string', required: false },
                { name: 'region', type: 'string', required: false },
                { name: 'score', type: 'number', required: false },
              ],
              outputVariables: ['primary', 'fallback', 'region', 'score'],
              ui: { position: { x: 120, y: 160 } },
            },
          },
          {
            nodeKey: 'variable_aggregation_1',
            type: 'VARIABLE_AGGREGATION',
            name: '变量聚合',
            config: {
              strategy: 'first_non_empty',
              groups: [
                {
                  name: 'Group1',
                  type: 'string',
                  variables: [
                    { value: '{{start.primary}}' },
                    { value: '{{start.fallback}}' },
                  ],
                },
                { name: 'Group2', type: 'string', variables: [{ value: '{{start.region}}' }] },
                { name: 'Score', variables: [{ value: '{{start.score}}' }] },
              ],
              outputParameters: [
                { name: 'Group1', type: 'string' },
                { name: 'Group2', type: 'string' },
              ],
              ui: { position: { x: 480, y: 160 } },
            },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { output: 'Group1={{variable_aggregation_1.Group1}};Group2={{variable_aggregation_1.Group2}};Score={{variable_aggregation_1.Score}}', ui: { position: { x: 860, y: 160 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'variable_aggregation_1', condition: null },
          { sourceNodeKey: 'variable_aggregation_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create workflow',
  )

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-variable_aggregation').waitFor({ state: 'visible', timeout: 10000 })
  const nodeCardText = await page.locator('.coze-node.node-variable_aggregation').innerText()
  assert(!nodeCardText.includes('未配置输入'), 'Variable aggregation node card must not render the generic input placeholder')
  assert(nodeCardText.includes('输出'), 'Variable aggregation node card should surface grouped outputs')
  await page.locator('.coze-node.node-variable_aggregation').click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })

  const panelText = await panel.innerText()
  assert(panelText.includes('聚合策略'), 'Expected official aggregation strategy section')
  assert(panelText.includes('返回每个分组中第一个非空的值'), 'Expected only first non-empty group strategy copy')
  assert(panelText.includes('新增分组'), 'Expected add group action')
  assert(!panelText.includes('高级/兼容配置'), 'Variable aggregation must not expose advanced compatibility section')
  assert(!panelText.includes('新增变量'), 'Variable aggregation groups should append a candidate row automatically instead of showing an add-variable button')
  assert(!panelText.includes('输入参数'), 'Variable aggregation must not render as a generic input-parameter node')
  assert(!panelText.includes('来源列表'), 'Variable aggregation must not render the old flat source-list editor')
  assert(!panelText.includes('拼接分隔符'), 'Variable aggregation must not expose non-official concat-only controls')
  assert(!panelText.includes('默认值'), 'Variable aggregation must not expose non-official default-value controls')
  assert(await panel.locator('[data-testid="aggregation-group-editor"]').count() === 1, 'Expected grouped aggregation editor')
  assert(await panel.locator('[data-testid="aggregation-group-card"]').count() === 3, 'Expected three aggregation groups')
  assert(await panel.locator('[data-testid="aggregation-group-name-display"]').count() === 3, 'Aggregation group names should render as read-first headers')
  assert(await panel.locator('[data-testid="aggregation-group-name-editor"]').count() === 0, 'Aggregation group names should not render as editable inputs by default')
  assert(await panel.locator('[data-testid="aggregation-group-variable-row"]').count() === 7, 'Expected grouped variable rows plus one automatic candidate row per group')
  assert(await panel.locator('[data-testid="aggregation-group-name-display"]').nth(0).innerText() === 'Group1', 'Expected Group1 to render as an aggregation output group')
  assert(await panel.locator('[data-testid="aggregation-group-name-display"]').nth(1).innerText() === 'Group2', 'Expected Group2 to render as an aggregation output group')
  assert(await panel.locator('[data-testid="aggregation-group-name-display"]').nth(2).innerText() === 'Score', 'Expected Score to render as an aggregation output group')
  assert(
    (await panel.locator('[data-testid="aggregation-group-card"]').nth(2).innerText()).includes('Number'),
    'Aggregation group type should be inferred from the selected variable reference',
  )
  await panel.locator('[data-testid="aggregation-group-name-display"]').nth(0).click()
  assert(await panel.locator('[data-testid="aggregation-group-name-editor"]').count() === 1, 'Clicking the group header should enter group-name edit mode')
  await panel.locator('[data-testid="aggregation-group-name-editor"]').fill('selected')
  await panel.locator('[data-testid="aggregation-group-name-editor"]').press('Enter')
  assert(await panel.locator('[data-testid="aggregation-group-name-editor"]').count() === 0, 'Confirming a group name should leave edit mode')
  assert(await panel.locator('[data-testid="aggregation-group-name-display"]').nth(0).innerText() === 'selected', 'Confirmed group name should render as a normal header')
  const scoreGroupCard = panel.locator('[data-testid="aggregation-group-card"]').nth(2)
  assert(
    await scoreGroupCard.locator('[data-testid="aggregation-group-variable-row"]').count() === 2,
    'Inferred numeric aggregation group should keep one selected variable plus one blank candidate row',
  )
  assert(
    !(await scoreGroupCard.innerText()).split(/\n/).some((line) => line.trim() === '0'),
    'Blank numeric aggregation candidate rows must not normalize into a visible zero value',
  )
  assert(await panel.locator('[data-testid="aggregation-output-summary"]').count() === 1, 'Variable aggregation outputs should be a read-only summary')
  assert(await panel.locator('[data-testid="aggregation-output-row"]').count() === 3, 'Variable aggregation output summary should follow group names')
  assert(
    (await panel.locator('[data-testid="aggregation-output-row"]').nth(2).innerText()).includes('Number'),
    'Variable aggregation output summary should preserve inferred group variable type',
  )
  assert(await panel.locator('[data-testid="output-parameter-editor"]').count() === 0, 'Variable aggregation must not use the generic editable output-parameter form')
  assert(!(await panel.innerText()).includes('输出格式'), 'Variable aggregation output section must not expose output format')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow variable aggregation official e2e')
} finally {
  await browser.close()
}
