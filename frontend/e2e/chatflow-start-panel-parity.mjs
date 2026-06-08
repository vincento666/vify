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
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `025.2 Start Panel ${Date.now()}`,
        description: 'start panel parity e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 140, y: 220 } } } },
          { nodeKey: 'llm_1', type: 'LLM', name: '大模型', config: { outputVariable: 'answer', ui: { position: { x: 520, y: 220 } } } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{llm_1.answer}}', ui: { position: { x: 900, y: 220 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create 025.2 chatflow',
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="start"]').click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assert((await panel.innerText()).includes('输入'), 'Expected START panel to expose 输入 section')
  assert(!(await panel.innerText()).includes('输出变量'), 'START panel should not expose separate 输出变量 section')

  const editor = panel.locator('[data-testid="start-variable-editor"]')
  await editor.waitFor({ state: 'visible', timeout: 5000 })
  const headerText = await editor.locator('[data-testid="start-variable-header"]').innerText()
  for (const column of ['变量名', '变量类型', '必填']) {
    assert(headerText.includes(column), `Expected START variable column ${column}, got ${headerText}`)
  }

  await editor.getByRole('button', { name: '添加开始变量', exact: true }).click()
  const rows = editor.locator('[data-testid="start-variable-row"]')
  const rowCount = await rows.count()
  assert(rowCount >= 2, `Expected default and custom START rows, got ${rowCount}`)
  const customRow = rows.nth(rowCount - 1)
  await customRow.getByPlaceholder('变量名').fill('ticket_id')
  await customRow.getByLabel('开始变量类型').click({ force: true })
  await page.locator('.el-select-dropdown__item', { hasText: 'str.' }).filter({ visible: true }).click()
  await customRow.getByLabel('开始变量必填').check()

  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForURL(`**/chatflows/${chatflow.id}/canvas`, { timeout: 10000 })
  await page.reload({ waitUntil: 'networkidle' })

  await page.locator('.vue-flow__node[data-id="llm_1"]').click()
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByRole('button', { name: '添加输入变量', exact: true }).click()
  const inputRow = panel.locator('[data-testid="input-parameter-row"]').first()
  await inputRow.getByPlaceholder('变量名').fill('ticket')
  await inputRow.getByRole('button', { name: '选择输入变量', exact: true }).click()
  const picker = inputRow.locator('[data-testid="input-variable-picker"]')
  await picker.waitFor({ state: 'visible', timeout: 5000 })
  await picker.locator('[data-testid="input-variable-source-item"]', { hasText: '开始' }).click()
  const itemText = await picker.locator('[data-testid="input-variable-item-list"]').innerText()
  assert(itemText.includes('ticket_id'), `Expected custom START variable in downstream picker, got ${itemText}`)
  await picker.locator('[data-testid="input-variable-option"]', { hasText: 'ticket_id' }).click()
  const chipText = await inputRow.locator('[data-testid="input-variable-chip"]').innerText()
  assert(chipText.includes('ticket_id'), `Expected ticket_id chip, got ${chipText}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS 025.2 chatflow start panel parity e2e chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
