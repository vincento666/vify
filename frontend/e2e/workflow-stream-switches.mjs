import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'

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
  const workflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/workflows`, {
      data: {
        name: `Stream Switches ${Date.now()}`,
        description: 'llm and agent stream switch e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['USER_INPUT'], ui: { position: { x: 120, y: 160 } } } },
          { nodeKey: 'llm_1', type: 'LLM', name: '大模型', config: { outputVariable: 'answer', ui: { position: { x: 460, y: 120 } } } },
          { nodeKey: 'agent_1', type: 'AGENT_CALL', name: '智能体', config: { targetAgentId: '', outputVariable: 'answer', ui: { position: { x: 460, y: 360 } } } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{llm_1.answer}}', ui: { position: { x: 860, y: 160 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create workflow stream switches',
  )

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas`, { waitUntil: 'networkidle' })
  for (const nodeId of ['llm_1', 'agent_1']) {
    await page.locator(`.vue-flow__node[data-id="${nodeId}"]`).click()
    const panel = page.getByTestId('node-config-panel')
    await panel.waitFor({ state: 'visible', timeout: 5000 })
    assert(await panel.getByRole('switch', { name: '流式输出', exact: true }).count() === 1, `Expected stream switch for ${nodeId}`)
    const switchRow = panel.locator('.switch-field-row').filter({ hasText: '流式输出' }).first()
    await switchRow.locator('.el-switch').click()
    const checked = await panel.getByRole('switch', { name: '流式输出', exact: true }).getAttribute('aria-checked')
    assert(checked === 'true', `Expected stream switch to be toggleable for ${nodeId}`)
    await panel.getByRole('button', { name: '关闭配置', exact: true }).click()
  }

  console.log('PASS workflow stream switches e2e')
} finally {
  await browser.close()
}
