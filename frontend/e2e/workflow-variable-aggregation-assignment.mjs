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

async function waitForRun(page, started, label) {
  if (started.output) return started
  assert(started.resultRef, `${label} missing resultRef`)
  const deadline = Date.now() + 10000
  let latest = started
  while (Date.now() < deadline) {
    latest = await unwrap(await page.request.get(`${baseUrl}${started.resultRef}`), `${label} result`)
    if (['SUCCEEDED', 'FAILED', 'INTERRUPTED'].includes(latest.status)) return latest
    await page.waitForTimeout(100)
  }
  throw new Error(`${label} timed out waiting for terminal result ${JSON.stringify(latest)}`)
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
  const startedRun = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
      data: { input: { primary: '', fallback: 'vip refund' } },
    }),
    'run variable workflow',
  )
  const run = await waitForRun(page, startedRun, 'run variable workflow')
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
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs-legacy`, {
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
  assert(await panel.locator('[data-testid="aggregation-group-editor"]').count() === 1, 'Expected grouped aggregation editor')
  assert(!panelText.includes('聚合来源值模式'), 'Aggregation editor must not expose reference/literal mode selector')
  assert(panelText.includes('返回每个分组中第一个非空的值'), 'Aggregation editor must expose the official first non-empty group strategy')
  assert(await panel.locator('[data-testid="aggregation-group-card"]').count() === 1, 'Legacy flat sources should fold into one aggregation group')
  assert(await panel.locator('[data-testid="aggregation-group-variable-row"]').count() === 3, 'Expected aggregation variable rows plus the automatic candidate row')
  assert(!panelText.includes('新增变量'), 'Aggregation groups should not expose a manual add-variable button')
  assert(await panel.locator('[data-testid="aggregation-variable-chip"]').count() >= 2, 'Expected aggregation references to render as variable chips')
  const aggregationRow = panel.locator('[data-testid="aggregation-group-variable-row"]').first()
  assert(
    await aggregationRow.getByTestId('structured-value-control').count() === 1,
    'Aggregation variable value must use the shared split variable/literal control',
  )
  assert(
    await aggregationRow.getByRole('button', { name: '选择聚合变量', exact: true }).count() === 1,
    'Aggregation variable must keep a persistent variable picker button',
  )
  assert(
    await aggregationRow.getByRole('button', { name: '清除聚合变量引用', exact: true }).count() === 1,
    'Aggregation referenced variable must expose a clear action',
  )
  await panel.getByRole('button', { name: '关闭配置' }).click()
  await panel.waitFor({ state: 'hidden', timeout: 5000 })

  await page.locator('.coze-node.node-variable_assign').click()
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  panelText = await panel.innerText()
  assert(!panelText.includes('目标作用域'), 'Assignment editor must not expose raw target scope as a primary field')
  assert(!panelText.includes('目标变量'), 'Assignment editor must not expose raw target variable as a primary field')
  assert(!panelText.includes('写入模式'), 'Assignment editor must not expose raw write mode as a primary field')
  assert(!panelText.includes('输出格式'), 'Assignment editor must not expose generic output format controls')
  assert(!panelText.includes('输出变量'), 'Assignment editor must not expose generic output variable controls')
  assert(!panelText.includes('赋值来源值模式'), 'Assignment editor must not expose reference/literal mode selector')
  assert(
    !panelText.includes('用于向变量赋值，实现数据的动态更新和传递'),
    'Assignment editor input section must not repeat task description copy',
  )
  assert(!panelText.includes('赋值类型'), 'Assignment editor must not expose write mode as an assignment type column')
  assert(await panel.locator('[data-testid="variable-assignment-editor"]').count() === 1, 'Expected structured assignment editor')
  assert(await panel.locator('.variable-assignment-task').count() === 0, 'Assignment editor must not render the redundant task intro block inside the input section')
  const assignmentHeaderText = await panel.locator('.variable-assignment-header').innerText()
  assert(assignmentHeaderText.includes('变量名称'), 'Assignment editor must show a target variable column')
  assert(!assignmentHeaderText.includes('类型'), 'Assignment editor must not show a redundant source type column')
  assert(assignmentHeaderText.includes('值'), 'Assignment editor must show assignment value column')
  assert(await panel.locator('[data-testid="variable-assignment-row"]').count() === 1, 'Expected assignment editor to render one assignment row')
  assert(await panel.locator('[data-testid="assignment-target-control"]').count() === 1, 'Expected assignment row to expose a writable target variable selector')
  const targetInput = panel.getByLabel('变量名称', { exact: true })
  assert(await targetInput.getAttribute('readonly') !== null, 'Assignment target name must not allow typing arbitrary new variables')
  assert(
    await targetInput.inputValue() === '',
    'Unconfigured assignment target must not render as a valid writable variable',
  )
  const assignmentEditor = panel.locator('[data-testid="variable-assignment-editor"]')
  await assignmentEditor.getByRole('button', { name: '选择写入变量', exact: true }).click()
  assert(
    await assignmentEditor.locator('[data-testid="assignment-target-source-item"]').count() === 0,
    'Assignment target picker must not treat existing assignment targets as configured writable variables',
  )
  await assignmentEditor.getByRole('button', { name: '选择写入变量', exact: true }).click()
  await assignmentEditor.getByTestId('assignment-target-picker').waitFor({ state: 'hidden', timeout: 5000 })
  assert(await panel.getByLabel('赋值来源类型', { exact: true }).count() === 0, 'Assignment row must not expose source type selector')
  assert(await panel.locator('[data-testid="assignment-value-control"]').count() === 1, 'Expected assignment row to expose a value input/reference control')
  assert(await panel.locator('[data-testid="assignment-variable-chip"]').count() === 1, 'Expected assignment source to render as variable chip')
  assert(
    await assignmentEditor.getByTestId('assignment-value-control').count() === 1,
    'Assignment source value must use the shared split variable/literal control',
  )
  assert(
    await assignmentEditor.getByRole('button', { name: '选择赋值内容变量', exact: true }).count() === 1,
    'Assignment source must keep a persistent variable picker button',
  )
  assert(
    await assignmentEditor.getByRole('button', { name: '切换为运算赋值', exact: true }).count() === 0,
    'Assignment source must not expose the unused fx operation toggle in the compact input section',
  )
  assert(
    await assignmentEditor.getByRole('button', { name: '清除赋值内容变量引用', exact: true }).count() === 1,
    'Assignment referenced source must expose a clear action',
  )
  await assignmentEditor.getByRole('button', { name: '清除赋值内容变量引用', exact: true }).click()
  assert(await assignmentEditor.getByTestId('assignment-variable-literal-input').inputValue() === '', 'Clearing assignment source must restore literal input mode')
  assert(await assignmentEditor.getByTestId('assignment-operation-control').count() === 0, 'Operation assignment controls must not render in the compact assignment editor')
  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow/chatflow variable aggregation assignment e2e')
} finally {
  await browser.close()
}
