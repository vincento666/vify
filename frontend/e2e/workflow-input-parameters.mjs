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

async function selectOption(page, label) {
  await page.locator('.el-select-dropdown__item', { hasText: label }).filter({ visible: true }).click()
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Workflow Input Params ${Date.now()}`

try {
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name,
        description: 'input parameter e2e',
        nodes: [
          {
            nodeKey: 'start',
            type: 'START',
            name: '开始',
            config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 160, y: 160 } } },
          },
          {
            nodeKey: 'llm_1',
            type: 'LLM',
            name: '大模型',
            config: { prompt: 'Return {{start.USER_INPUT}}', outputVariable: 'answer', ui: { position: { x: 520, y: 160 } } },
          },
          {
            nodeKey: 'end',
            type: 'END',
            name: '结束',
            config: { outputVariable: 'output', output: '{{llm_1.answer}}', ui: { position: { x: 880, y: 160 } } },
          },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create input parameter workflow',
  )

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()

  let panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  let editor = panel.locator('[data-testid="input-parameter-editor"]')
  await editor.waitFor({ state: 'visible', timeout: 5000 })

  await editor.getByRole('button', { name: '添加输入变量', exact: true }).click()
  await editor.getByRole('button', { name: '添加输入变量', exact: true }).click()

  let rows = editor.locator('[data-testid="input-parameter-row"]')
  assert(await rows.count() === 2, 'Expected two input parameter rows')

  await rows.nth(0).getByPlaceholder('变量名').fill('question')
  await rows.nth(0).getByRole('button', { name: '选择输入变量' }).click()
  let picker = rows.nth(0).locator('[data-testid="input-variable-picker"]')
  await picker.waitFor({ state: 'visible', timeout: 5000 })
  await picker.locator('[data-testid="input-variable-source-item"]', { hasText: '开始' }).click()
  await picker.locator('[data-testid="input-variable-flyout"]').waitFor({ state: 'visible', timeout: 5000 })
  await picker.locator('[data-testid="input-variable-option"]', { hasText: 'USER_INPUT' }).click()

  await rows.nth(1).getByPlaceholder('变量名').fill('limit')
  await rows.nth(1).getByLabel('输入变量类型').click({ force: true })
  await selectOption(page, 'num.')
  await rows.nth(1).getByLabel('输入变量值').fill('3')

  const duplicateText = await editor.innerText()
  assert(!duplicateText.includes('需要选择引用变量'), 'Expected reference validation to clear after choosing start variable')

  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForURL('**/workflows/*/canvas', { timeout: 10000 })
  await page.reload({ waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()

  panel = page.locator('[data-testid="node-config-panel"]')
  editor = panel.locator('[data-testid="input-parameter-editor"]')
  rows = editor.locator('[data-testid="input-parameter-row"]')
  assert(await rows.count() === 2, 'Expected input parameter rows to persist after reopen')

  const persistedRows = await rows.evaluateAll((elements) => elements.map((element) => ({
    name: element.querySelector('input[placeholder="变量名"]')?.value || '',
    text: element.textContent || '',
    inputs: Array.from(element.querySelectorAll('input')).map((input) => input.value),
  })))

  assert(persistedRows[0].name === 'question', 'Expected first input name to persist')
  assert(persistedRows[0].inputs.includes('{{start.USER_INPUT}}'), 'Expected reference value to persist')
  assert(persistedRows[1].name === 'limit', 'Expected second input name to persist')
  assert(persistedRows[1].text.includes('num.'), 'Expected numeric type to persist')
  assert(!persistedRows[1].text.includes('字面量') && !persistedRows[1].text.includes('引用'), 'Expected literal/reference mode selector copy to stay hidden')
  assert(persistedRows[1].inputs.includes('3'), 'Expected literal number value to persist')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow input parameter editor e2e')
} finally {
  await browser.close()
}
