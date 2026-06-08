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
        name: `015.2 Variable Workflow ${Date.now()}`,
        description: 'aggregation and assignment e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['primary', 'fallback'], ui: { position: { x: 120, y: 120 } } } },
          {
            nodeKey: 'variable_aggregation_1',
            type: 'VARIABLE_AGGREGATION',
            name: '变量聚合',
            config: {
              strategy: 'first_non_empty',
              sources: [
                { name: 'primary', value: '{{start.primary}}' },
                { name: 'fallback', value: '{{start.fallback}}' },
              ],
              defaultValue: 'default',
              outputVariable: 'selected',
              ui: { position: { x: 460, y: 120 } },
            },
          },
          {
            nodeKey: 'variable_assign_1',
            type: 'VARIABLE_ASSIGN',
            name: '变量赋值',
            config: {
              targetScope: 'flow',
              targetVariable: 'route',
              source: '{{variable_aggregation_1.selected}}',
              writeMode: 'set',
              ui: { position: { x: 800, y: 120 } },
            },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'route={{flow.route}}', ui: { position: { x: 1120, y: 120 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'variable_aggregation_1', condition: null },
          { sourceNodeKey: 'variable_aggregation_1', targetNodeKey: 'variable_assign_1', condition: null },
          { sourceNodeKey: 'variable_assign_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create variable workflow',
  )
  const run = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
      data: { input: { primary: '', fallback: 'vip refund' } },
    }),
    'run variable workflow',
  )
  assert(run.output.final === 'route=vip refund', `Unexpected workflow output ${JSON.stringify(run.output)}`)

  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `015.2 Variable Chatflow ${Date.now()}`,
        description: 'conversation assignment e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 120, y: 120 } } } },
          {
            nodeKey: 'variable_assign_1',
            type: 'VARIABLE_ASSIGN',
            name: '变量赋值',
            config: { targetScope: 'conversation', targetVariable: 'topic', source: '{{start.sys.query}}', writeMode: 'set', ui: { position: { x: 520, y: 120 } } },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'topic={{conversation.topic}}', ui: { position: { x: 860, y: 120 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'variable_assign_1', condition: null },
          { sourceNodeKey: 'variable_assign_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create variable chatflow',
  )
  const chatRun = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
      data: { input: { 'sys.query': 'refund topic' } },
    }),
    'run variable chatflow',
  )
  assert(chatRun.output.final === 'topic=refund topic', `Unexpected chatflow output ${JSON.stringify(chatRun.output)}`)

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-variable_aggregation').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.coze-node.node-variable_assign').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByLabel('添加节点').click()
  const palette = page.locator('[data-testid="bottom-node-palette"]')
  await palette.waitFor({ state: 'visible', timeout: 5000 })
  const paletteText = await palette.innerText()
  assert(paletteText.includes('变量聚合'), 'Expected palette to expose runnable variable aggregation')
  assert(paletteText.includes('变量赋值'), 'Expected palette to expose runnable variable assignment')
  assert(!paletteText.includes('循环'), 'Loop must not be exposed as runnable in 015.2')
  assert(!paletteText.includes('批处理'), 'Batch must not be exposed as runnable in 015.2')
  assert(!paletteText.includes('异步任务'), 'Async task must not be exposed as runnable in 015.2')
  await page.getByLabel('添加节点').click({ force: true })
  await palette.waitFor({ state: 'hidden', timeout: 5000 })

  await page.locator('.coze-node.node-variable_aggregation').click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  let panelText = await panel.innerText()
  assert(await panel.locator('[data-testid="aggregation-source-editor"]').count() === 1, 'Expected structured aggregation source editor')
  assert(!panelText.includes('聚合来源值模式'), 'Aggregation editor must not expose reference/literal mode selector')
  assert(await panel.locator('[data-testid="aggregation-source-row"]').count() === 2, 'Expected aggregation source rows')
  assert(await panel.locator('[data-testid="aggregation-variable-chip"]').count() >= 2, 'Expected aggregation references to render as variable chips')
  const aggregationRow = panel.locator('[data-testid="aggregation-source-row"]').first()
  assert(
    await aggregationRow.getByTestId('structured-value-control').count() === 1,
    'Aggregation source value must use the shared split variable/literal control',
  )
  assert(
    await aggregationRow.getByRole('button', { name: '选择聚合来源变量', exact: true }).count() === 1,
    'Aggregation source must keep a persistent variable picker button',
  )
  assert(
    await aggregationRow.getByRole('button', { name: '清除聚合来源变量引用', exact: true }).count() === 1,
    'Aggregation referenced source must expose a clear action',
  )
  await panel.getByRole('button', { name: '关闭配置' }).click()
  await panel.waitFor({ state: 'hidden', timeout: 5000 })

  await page.locator('.coze-node.node-variable_assign').click()
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  panelText = await panel.innerText()
  assert(!panelText.includes('目标作用域'), 'Assignment editor must not expose raw target scope as a primary field')
  assert(!panelText.includes('目标变量'), 'Assignment editor must not expose raw target variable as a primary field')
  assert(!panelText.includes('写入模式'), 'Assignment editor must not expose raw write mode as a primary field')
  assert(!panelText.includes('赋值来源值模式'), 'Assignment editor must not expose reference/literal mode selector')
  assert(panelText.includes('变量赋值'), 'Assignment editor must use a task-first variable assignment section')
  assert(panelText.includes('变量名'), 'Assignment editor must show a target variable column')
  assert(panelText.includes('赋值类型'), 'Assignment editor must show assignment type column')
  assert(panelText.includes('变量值'), 'Assignment editor must show assignment value column')
  assert(await panel.locator('[data-testid="variable-assignment-editor"]').count() === 1, 'Expected structured assignment editor')
  assert(await panel.locator('[data-testid="variable-assignment-row"]').count() === 1, 'Expected assignment editor to render one assignment row')
  assert(await panel.locator('[data-testid="assignment-target-control"]').count() === 1, 'Expected assignment row to expose a writable target variable selector')
  assert(await panel.locator('[data-testid="assignment-value-control"]').count() === 1, 'Expected assignment row to expose a value input/reference control')
  assert(await panel.locator('[data-testid="assignment-variable-chip"]').count() === 1, 'Expected assignment source to render as variable chip')
  const assignmentEditor = panel.locator('[data-testid="variable-assignment-editor"]')
  assert(
    await assignmentEditor.getByTestId('assignment-value-control').count() === 1,
    'Assignment source value must use the shared split variable/literal control',
  )
  assert(
    await assignmentEditor.getByRole('button', { name: '选择赋值内容变量', exact: true }).count() === 1,
    'Assignment source must keep a persistent variable picker button',
  )
  assert(
    await assignmentEditor.getByRole('button', { name: '清除赋值内容变量引用', exact: true }).count() === 1,
    'Assignment referenced source must expose a clear action',
  )
  await assignmentEditor.getByRole('button', { name: '清除赋值内容变量引用', exact: true }).click()
  assert(await assignmentEditor.getByTestId('assignment-variable-literal-input').inputValue() === '', 'Clearing assignment source must restore literal input mode')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow/chatflow variable aggregation assignment e2e')
} finally {
  await browser.close()
}
