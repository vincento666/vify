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
const marker = Date.now()

try {
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name: `Condition branch values ${marker}`,
        description: 'condition branch variable picker e2e',
        nodes: [
          {
            nodeKey: 'start',
            type: 'START',
            name: '开始',
            config: {
              outputVariables: ['USER_INPUT', 'intent'],
              ui: { position: { x: 160, y: 220 } },
            },
          },
          {
            nodeKey: 'router',
            type: 'CONDITION',
            name: '选择器',
            config: {
              outputVariable: 'route',
              defaultBranch: 'fallback',
              conditionBranches: [
                {
                  key: 'matched',
                  logic: 'AND',
                  conditions: [{ left: '{{start.USER_INPUT}}', operator: 'equals', right: '' }],
                },
              ],
              ui: { position: { x: 500, y: 220 } },
            },
          },
          {
            nodeKey: 'matched',
            type: 'END',
            name: '匹配',
            config: { outputVariable: 'output', output: 'matched', ui: { position: { x: 840, y: 140 } } },
          },
          {
            nodeKey: 'fallback',
            type: 'END',
            name: '兜底',
            config: { outputVariable: 'output', output: 'fallback', ui: { position: { x: 840, y: 320 } } },
          },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'router', condition: null },
          { sourceNodeKey: 'router', targetNodeKey: 'matched', condition: 'matched' },
          { sourceNodeKey: 'router', targetNodeKey: 'fallback', condition: null },
        ],
      },
    }),
    'create condition workflow',
  )

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="router"]').click()

  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const editor = panel.getByTestId('condition-branch-editor')
  await editor.waitFor({ state: 'visible', timeout: 5000 })
  const branch = editor.getByTestId('condition-branch-card').first()
  const row = branch.getByTestId('condition-row').first()

  const rowText = await row.innerText()
  assert(!rowText.includes('引用') && !rowText.includes('字面量'), `Condition row must not expose mode copy, got ${rowText}`)

  const operandControls = row.getByTestId('condition-operand-control')
  assert(await operandControls.count() === 2, 'Condition row must render left and right split operand controls')
  const leftOperand = operandControls.nth(0)
  const rightOperand = operandControls.nth(1)
  assert(
    await leftOperand.getByRole('button', { name: '选择左值变量', exact: true }).count() === 1,
    'Condition left operand must keep a persistent variable picker button',
  )
  assert(
    await leftOperand.getByRole('button', { name: '清除左值变量引用', exact: true }).count() === 1,
    'Condition referenced left operand must expose a clear action',
  )
  assert(
    await rightOperand.getByRole('button', { name: '选择右值变量', exact: true }).count() === 1,
    'Condition right operand must keep a persistent variable picker button before a value is selected',
  )

  const rightValue = row.getByLabel('条件右值')
  await rightValue.fill('{')
  assert(await rightValue.inputValue() === '{{}}', 'Typing { in condition value should auto-complete to {{}}')

  const picker = row.getByTestId('condition-variable-picker')
  await picker.waitFor({ state: 'visible', timeout: 5000 })
  const pickerText = await picker.innerText()
  assert(pickerText.includes('开始'), `Expected condition picker to show connected START source, got ${pickerText}`)
  for (const staleSource of ['用户变量', '应用变量', '会话变量', '系统变量', '用户画像']) {
    assert(!pickerText.includes(staleSource), `Condition picker should hide unused static source ${staleSource}, got ${pickerText}`)
  }
  await picker.locator('[data-testid="condition-variable-source-item"]', { hasText: '开始' }).click()
  await picker.locator('[data-testid="condition-variable-option"]', { hasText: 'intent' }).click()

  const selectedValue = await row.getByLabel('条件右值').inputValue()
  assert(selectedValue === '{{start.intent}}', `Expected selected condition variable reference, got ${selectedValue}`)
  assert(await row.getByTestId('condition-variable-chip').count() >= 2, 'Expected condition variables to render as chips')
  assert(
    await rightOperand.getByRole('button', { name: '清除右值变量引用', exact: true }).count() === 1,
    'Condition referenced right operand must expose a clear action',
  )
  await rightOperand.getByRole('button', { name: '清除右值变量引用', exact: true }).click()
  assert(await rightValue.inputValue() === '', 'Clearing a condition variable chip must restore literal input mode')

  const addCondition = branch.getByRole('button', { name: '添加条件', exact: true })
  const conditionSection = page.getByTestId('config-section-条件分支')
  const addBranch = conditionSection.locator('.section-title').getByRole('button', { name: '添加条件分支', exact: true })
  assert(await addCondition.locator('svg').count() >= 1, 'Add condition button must use an icon')
  assert(await addBranch.count() === 1, 'Add branch button must live in the condition section header')
  assert(await addBranch.locator('svg').count() >= 1, 'Add branch button must use an icon')
  assert(
    await editor.getByRole('button', { name: '添加条件分支', exact: true }).count() === 0,
    'Condition editor must not render a duplicate bottom add-branch button',
  )

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow condition branch values e2e')
} finally {
  await browser.close()
}
