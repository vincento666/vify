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
        name: `025.4 LLM Panel ${Date.now()}`,
        description: 'llm panel parity e2e',
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
    'create 025.4 chatflow',
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.vue-flow__node[data-id="llm_1"]').click()
  const panel = page.getByTestId('node-config-panel')
  await panel.waitFor({ state: 'visible', timeout: 5000 })

  const order = await panel.evaluate(() => {
    const ids = [
      'llm-mode-section',
      'llm-model-section',
      'llm-resource-section',
      'config-section-输入',
      'config-section-系统提示词',
      'config-section-用户提示词',
      'config-section-输出',
    ]
    return ids.map((id) => {
      const element = document.querySelector(`[data-testid="${id}"]`)
      if (!element) return { id, missing: true, top: -1 }
      return { id, missing: false, top: element.getBoundingClientRect().top }
    })
  })

  const missing = order.filter((item) => item.missing).map((item) => item.id)
  assert(missing.length === 0, `Expected LLM panel sections, missing ${missing.join(', ')}`)
  for (let index = 1; index < order.length; index += 1) {
    assert(order[index - 1].top < order[index].top, `Expected LLM section order ${JSON.stringify(order)}`)
  }

  const systemSection = panel.getByTestId('config-section-系统提示词')
  const userSection = panel.getByTestId('config-section-用户提示词')
  assert(await systemSection.getByRole('button', { name: '变量', exact: true }).count() === 0, 'Expected system prompt to use inline {{ variable picker')
  assert(await userSection.getByRole('button', { name: '变量', exact: true }).count() === 0, 'Expected user prompt to use inline {{ variable picker')
  assert(await panel.getByTestId('config-section-输出').getByTestId('output-parameter-row').count() >= 1, 'Expected LLM output rows')

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS 025.4 chatflow llm panel parity e2e chatflow=${chatflow.id}`)
} finally {
  await browser.close()
}
