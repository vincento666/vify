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
const name = `Chatflow Params ${Date.now()}`

try {
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name,
        description: 'chatflow parameter e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query', 'sys.conversation_id'], ui: { position: { x: 140, y: 220 } } } },
          { nodeKey: 'llm_1', type: 'LLM', name: '大模型', config: { outputVariable: 'answer', ui: { position: { x: 520, y: 220 } } } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{llm_1.answer}}', ui: { position: { x: 900, y: 220 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create chatflow parameters graph',
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-llm').click()

  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assert((await panel.innerText()).includes('会话历史'), 'Expected Chatflow LLM input section to expose history toggle')
  await panel.getByLabel('会话历史').check()

  await panel.getByRole('button', { name: '添加输入变量', exact: true }).click()
  const inputRow = panel.locator('[data-testid="input-parameter-row"]').first()
  await inputRow.getByPlaceholder('变量名').fill('query')
  await inputRow.getByRole('button', { name: '选择输入变量', exact: true }).click()
  const picker = page.locator('[data-testid="input-variable-picker"]')
  await picker.locator('[data-testid="input-variable-source-item"]', { hasText: '开始' }).click()
  await picker.locator('[data-testid="input-variable-option"]', { hasText: 'sys.query' }).click()

  await panel.locator('[data-testid="output-parameter-row"]').first().getByPlaceholder('变量名').fill('answer')
  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForURL('**/chatflows/*/canvas', { timeout: 10000 })
  await page.reload({ waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-llm').click()
  await panel.waitFor({ state: 'visible', timeout: 5000 })

  assert(await panel.getByLabel('会话历史').isChecked(), 'Expected history toggle to persist')
  const persistedRow = panel.locator('[data-testid="input-parameter-row"]').first()
  assert(await persistedRow.locator('[aria-label="输入引用变量"]').inputValue() === '{{start.sys.query}}', 'Expected START sys.query input reference to persist')
  assert(await panel.locator('[data-testid="output-parameter-row"]').first().getByPlaceholder('变量名').inputValue() === 'answer', 'Expected output variable to persist')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow input output controls e2e')
} finally {
  await browser.close()
}
