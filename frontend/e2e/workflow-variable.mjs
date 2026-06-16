import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const name = `Workflow Variable ${Date.now()}`

async function unwrap(response, label) {
  assert(response.ok(), `${label} HTTP ${response.status()}`)
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

try {
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name,
        description: 'variable picker e2e',
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
            config: {
              prompt: 'Return {{start.USER_INPUT}}',
              outputFormat: 'JSON',
              outputParameters: [
                { name: 'answer', type: 'string' },
                { name: 'reasoning', type: 'object' },
              ],
              outputVariable: 'answer',
              ui: { position: { x: 520, y: 160 } },
            },
          },
          {
            nodeKey: 'end',
            type: 'END',
            name: '结束',
            config: {
              outputVariable: 'output',
              outputParameters: [{ name: 'final', type: 'string' }],
              output: '',
              ui: { position: { x: 880, y: 160 } },
            },
          },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create variable picker workflow',
  )

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="end"]').click()

  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  const responseInput = panel.getByPlaceholder('返回给调用方的文本，可使用变量引用')
  await responseInput.fill('{')
  const picker = panel.locator('[data-testid="variable-picker"]')
  await picker.waitFor({ state: 'visible', timeout: 5000 })

  const pickerText = await picker.innerText()
  assert(pickerText.includes('final'), `Expected local final variable, got ${pickerText}`)
  assert(!pickerText.includes('{{'), `Inline picker must show compact variable labels instead of raw references, got ${pickerText}`)
  assert(!pickerText.includes('global.brand'), `Inline picker must not expose global variables directly, got ${pickerText}`)
  assert(!pickerText.includes('sys.now'), `Inline picker must not expose system variables directly, got ${pickerText}`)
  assert(!pickerText.includes(`${llmNodeKey(workflow)}.answer`), `Inline picker must not expose upstream variables directly, got ${pickerText}`)

  const itemListText = await picker.locator('[data-testid="inline-variable-list"]').innerText()
  assert(itemListText.includes('final'), 'Expected local final output in inline list')
  await picker.locator('[data-testid="variable-option"]', { hasText: 'final' }).click()

  const outputValue = await responseInput.inputValue()
  assert(outputValue.includes('{{final}}'), 'Expected variable selector to insert local output reference')

  await page.locator('.canvas-actions').getByRole('button', { name: '保存', exact: true }).click()
  await page.waitForURL('**/workflows/*/canvas', { timeout: 10000 })
  await page.reload({ waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="end"]').click()
  const reopenedOutput = await panel.getByPlaceholder('返回给调用方的文本，可使用变量引用').inputValue()
  assert(reopenedOutput.includes('{{final}}'), 'Expected local variable reference to persist after reopen')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS workflow variable selector e2e')
} finally {
  await browser.close()
}

function llmNodeKey(workflow) {
  return workflow.nodes.find((node) => node.type === 'LLM')?.nodeKey || 'llm_1'
}
