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
        name: `025.1 Variable Reference ${Date.now()}`,
        description: 'variable reference foundation e2e',
        nodes: [
          {
            nodeKey: 'start',
            type: 'START',
            name: '开始',
            config: {
              outputVariables: ['USER_INPUT', 'CONVERSATION_NAME'],
              ui: { position: { x: 120, y: 220 } },
            },
          },
          {
            nodeKey: 'llm_1',
            type: 'LLM',
            name: '大模型',
            config: {
              prompt: '回答用户问题',
              outputVariable: 'answer',
              ui: { position: { x: 520, y: 220 } },
            },
          },
          {
            nodeKey: 'end',
            type: 'END',
            name: '结束',
            config: {
              outputVariable: 'output',
              output: '{{llm_1.answer}}',
              ui: { position: { x: 900, y: 220 } },
            },
          },
          {
            nodeKey: 'ghost_1',
            type: 'LLM',
            name: '断开模型',
            config: {
              outputVariable: 'ghost_answer',
              ui: { position: { x: 520, y: 520 } },
            },
          },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create 025.1 chatflow',
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  await panel.getByRole('button', { name: '添加输入变量', exact: true }).click()

  const row = panel.locator('[data-testid="input-parameter-row"]').first()
  await row.getByPlaceholder('变量名').fill('query')
  await row.getByRole('button', { name: '选择输入变量', exact: true }).click()

  const picker = row.locator('[data-testid="input-variable-picker"]')
  await picker.waitFor({ state: 'visible', timeout: 5000 })
  const sourceText = await picker.locator('[data-testid="input-variable-source-list"]').innerText()
  assert(sourceText.includes('开始'), `Expected default Chatflow picker to expose connected START source, got ${sourceText}`)
  for (const staleSource of ['用户变量', '应用变量', '系统变量', '会话变量', '用户画像']) {
    assert(!sourceText.includes(staleSource), `Expected picker to hide stale source ${staleSource}, got ${sourceText}`)
  }
  assert(!sourceText.includes('断开模型'), 'Disconnected node output source must not be selectable')
  assert(!sourceText.includes('结束'), 'Downstream node output source must not be selectable')
  assert(await picker.locator('[data-testid="variable-source-arrow"]').count() >= 1, 'Expandable START source should show a right chevron')

  await picker.locator('[data-testid="input-variable-source-item"]', { hasText: '开始' }).click()
  const startList = await picker.locator('[data-testid="input-variable-item-list"]').innerText()
  assert(startList.includes('USER_INPUT'), `Expected START USER_INPUT variable, got ${startList}`)
  assert(startList.includes('CONVERSATION_NAME'), `Expected START CONVERSATION_NAME variable, got ${startList}`)
  assert(startList.includes('String'), `Expected full type label in variable list, got ${startList}`)
  assert(!startList.includes('str.'), `Variable list should not use compact type labels, got ${startList}`)
  assert(!startList.includes('start.USER_INPUT'), `Variable list should not prefix node variables, got ${startList}`)
  assert(!startList.includes('sys.query'), `Default Chatflow picker should not expose sys.query, got ${startList}`)
  await picker.locator('[data-testid="input-variable-option"]', { hasText: 'USER_INPUT' }).click()

  const chip = row.locator('[data-testid="input-variable-chip"]')
  await chip.waitFor({ state: 'visible', timeout: 5000 })
  const chipText = await chip.innerText()
  assert(chipText.includes('USER_INPUT'), `Expected chip to show USER_INPUT variable, got ${chipText}`)
  assert(chipText.includes('str.'), `Expected chip to show compact type, got ${chipText}`)
  assert(!chipText.includes('{{') && !chipText.includes('开始.'), `Expected chip to omit source/reference description, got ${chipText}`)

  await chip.getByRole('button', { name: '清除输入变量引用', exact: true }).click()
  assert(await row.locator('[data-testid="input-variable-chip"]').count() === 0, 'Expected chip to clear')
  assert(await row.getByLabel('输入变量值').count() === 1, 'Expected direct literal input after clear')
  assert(await row.getByRole('button', { name: '选择输入变量', exact: true }).count() === 1, 'Expected reference shortcut after clear')

  await row.getByRole('button', { name: '选择输入变量', exact: true }).click()
  await picker.locator('[data-testid="input-variable-source-item"]', { hasText: '开始' }).click()
  await picker.locator('[data-testid="input-variable-option"]', { hasText: 'CONVERSATION_NAME' }).click()
  const conversationNameChipText = await chip.innerText()
  assert(conversationNameChipText.includes('CONVERSATION_NAME'), `Expected conversation name chip, got ${conversationNameChipText}`)
  assert(!conversationNameChipText.includes('{{') && !conversationNameChipText.includes('开始.'), `Expected chip to omit source/reference description, got ${conversationNameChipText}`)

  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForURL(`**/chatflows/${chatflow.id}/canvas`, { timeout: 10000 })
  await page.reload({ waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()
  const persistedChip = panel.locator('[data-testid="input-variable-chip"]')
  await persistedChip.waitFor({ state: 'visible', timeout: 5000 })
  assert((await persistedChip.innerText()).includes('CONVERSATION_NAME'), 'Expected START variable chip to persist after reload')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS 025.1 chatflow variable reference foundation e2e chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
