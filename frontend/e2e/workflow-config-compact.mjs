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
  await page.goto(`${baseUrl}/workflows/create`, { waitUntil: 'networkidle' })
  const toolbar = page.locator('[data-testid="canvas-bottom-toolbar"]')
  await toolbar.waitFor({ state: 'visible', timeout: 5000 })
  await toolbar.getByRole('button', { name: '添加节点', exact: true }).click()
  await page.getByTestId('bottom-node-palette').getByRole('button', { name: '大模型', exact: true }).click()
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()

  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assert(await panel.getByText('节点名称', { exact: true }).count() === 0, 'Expected node name field removed')
  assert(await panel.getByRole('button', { name: '添加输入变量', exact: true }).count() === 1, 'Expected one input add button')

  const inputEditor = panel.getByTestId('input-parameter-editor')
  await inputEditor.getByRole('button', { name: '添加输入变量', exact: true }).click()
  const inputRow = inputEditor.getByTestId('input-parameter-row').first()
  await inputRow.waitFor({ state: 'visible', timeout: 5000 })
  const inputText = await inputRow.innerText()
  assert(inputText.includes('str.'), 'Expected compact input type label')
  assert(!inputText.includes('String'), 'Expected full input type label removed')
  const inputBox = await inputRow.boundingBox()
  assert(inputBox && inputBox.height <= 48, `Expected compact input row height, got ${inputBox?.height}`)

  const outputRow = panel.getByTestId('output-parameter-row').first()
  const outputText = await outputRow.innerText()
  assert(outputText.includes('str.'), 'Expected compact output type label')
  assert(!outputText.includes('String'), 'Expected full output type label removed')
  const outputBox = await outputRow.boundingBox()
  assert(outputBox && outputBox.height <= 44, `Expected compact output row height, got ${outputBox?.height}`)

  const textareaResize = await panel.locator('textarea').first().evaluate((el) => getComputedStyle(el).resize)
  assert(textareaResize === 'none', `Expected textarea resize none, got ${textareaResize}`)

  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `Config Header Message ${Date.now()}`,
        description: 'config compact message header e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 120, y: 160 } } } },
          { nodeKey: 'message_1', type: 'MESSAGE', name: '消息', config: { content: 'Hello', outputVariable: 'content', streamOutput: 'enabled', ui: { position: { x: 420, y: 160 } } } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{message_1.content}}', ui: { position: { x: 720, y: 160 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'message_1', condition: null },
          { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create chatflow for config compact',
  )
  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="message_1"]').click()
  const messagePanel = page.locator('[data-testid="node-config-panel"]')
  await messagePanel.waitFor({ state: 'visible', timeout: 5000 })
  const messageHeaderText = await messagePanel.locator('.config-header').innerText()
  assert(messageHeaderText.includes('消息'), `Expected config header to keep the node display name, got ${messageHeaderText}`)
  assert(!messageHeaderText.includes('message_1'), `Config header must not expose node key, got ${messageHeaderText}`)
  assert(await messagePanel.getByRole('switch', { name: '流式输出', exact: true }).count() === 1, 'Expected stream output switch')
  const switchAlignment = await messagePanel.locator('.switch-field-row').filter({ hasText: '流式输出' }).first().evaluate((row) => {
    const label = row.querySelector('span')?.getBoundingClientRect()
    const control = row.querySelector('.el-switch')?.getBoundingClientRect()
    const bounds = row.getBoundingClientRect()
    return {
      labelLeft: label?.left ?? 0,
      controlRight: control?.right ?? 0,
      rowLeft: bounds.left,
      rowRight: bounds.right,
    }
  })
  assert(switchAlignment.labelLeft - switchAlignment.rowLeft < 8, `Switch label must stay left aligned ${JSON.stringify(switchAlignment)}`)
  assert(Math.abs(switchAlignment.rowRight - switchAlignment.controlRight) < 8, `Switch control must be right aligned ${JSON.stringify(switchAlignment)}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow config compact e2e')
} finally {
  await browser.close()
}
