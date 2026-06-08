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
        name: `025.3 End Panel ${Date.now()}`,
        description: 'end panel parity e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 120, y: 220 } } } },
          { nodeKey: 'llm_1', type: 'LLM', name: '大模型', config: { outputVariable: 'answer', ui: { position: { x: 520, y: 220 } } } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'output', output: '{{llm_1.answer}}', ui: { position: { x: 900, y: 220 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create 025.3 chatflow',
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="end"]').click()

  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assert(await panel.getByTestId('config-section-输入').count() === 0, 'END panel must not expose input parameters section')

  const outputSection = panel.getByTestId('config-section-输出')
  const editor = outputSection.getByTestId('output-parameter-editor')
  await editor.waitFor({ state: 'visible', timeout: 5000 })
  assert(await outputSection.getByTestId('end-response-editor').count() === 0, 'END return mode tabs must not be nested in 输出 section')

  const modeSection = panel.getByTestId('end-return-mode-section')
  const mode = modeSection.getByTestId('end-return-mode')
  await mode.waitFor({ state: 'visible', timeout: 5000 })
  assert((await mode.innerText()).includes('返回文本'), 'Expected END return mode to include 返回文本')
  assert((await mode.innerText()).includes('返回变量'), 'Expected END return mode to include 返回变量')

  assert(await editor.getByLabel('输出格式').count() === 1, 'Expected END output format selector')
  assert(await editor.getByLabel('回答内容').count() === 0, 'Expected END answer content outside 输出 section')
  assert(await editor.getByTestId('output-parameter-row').count() >= 1, 'Expected END text return mode to show output variable rows')
  const answerSection = panel.getByTestId('config-section-回答内容')
  await answerSection.waitFor({ state: 'visible', timeout: 5000 })
  assert(await answerSection.getByLabel('流式输出').count() === 1, 'Expected END stream switch')
  assert(await answerSection.getByLabel('回答内容').count() === 1, 'Expected END answer content textarea')
  assert(await answerSection.getByRole('button', { name: '插入响应变量', exact: true }).count() === 0, 'Expected END response variable insert button removed')

  await modeSection.getByRole('button', { name: '返回变量', exact: true }).click()
  assert(await editor.getByTestId('output-parameter-row').count() >= 1, 'Expected END variable return mode to show output variable rows')
  assert(await editor.getByLabel('输出格式').count() === 1, 'Expected END output format selector in variable return mode')
  assert(await panel.getByTestId('config-section-回答内容').count() === 0, 'Expected END variable return mode to hide answer content')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS 025.3 chatflow end panel parity e2e chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
