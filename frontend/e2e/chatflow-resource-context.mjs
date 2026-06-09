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
        name: `Chatflow Resource ${Date.now()}`,
        description: 'chatflow resource context e2e',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'], ui: { position: { x: 160, y: 180 } } } },
          {
            nodeKey: 'llm',
            type: 'LLM',
            name: '大模型',
            config: {
              prompt: '只从 Knowledge Context 提取答案。请复制其中 The approved refund answer is 后面的完整代号，不要解释。用户问题：{{sys.query}}',
              outputVariable: 'answer',
              includeHistory: 'true',
              resources: [{ type: 'KNOWLEDGE_BASE', knowledgeBaseId: 348, query: 'The approved refund answer is', topK: 1 }],
              ui: { position: { x: 520, y: 160 } },
            },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'answer', ui: { position: { x: 860, y: 180 } } } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm', condition: null },
          { sourceNodeKey: 'llm', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create chatflow resource workflow',
  )

  await page.goto(`${baseUrl}/chatflows/${chatflow.id}/canvas`, { waitUntil: 'networkidle' })
  await page.locator('.coze-node.node-llm').click()
  const panel = page.locator('[data-testid="node-config-panel"]')
  await panel.waitFor({ state: 'visible', timeout: 5000 })
  assert(await panel.getByLabel('会话历史').isChecked(), 'Expected include history toggle to be enabled')
  assert((await panel.locator('[data-testid="llm-resource-section"]').innerText()).includes('运行时会检索并注入模型上下文'), 'Expected Knowledge resource support state')

  const runResponse = await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
    data: { input: { 'sys.query': '退款批准答案是什么' } },
    timeout: 60000,
  })
  if (runResponse.ok()) {
    const runPayload = await runResponse.json()
    assert(runPayload.code === 200, `run API ${runPayload.message}`)
    assert(runPayload.data.status === 'SUCCEEDED', `Expected SUCCEEDED, got ${runPayload.data.status}`)
    assert(
      String(runPayload.data.output.answer).includes('KB_CONDITION_KC_1780317732926'),
      `Expected Knowledge-backed token, got ${JSON.stringify(runPayload.data.output)}`,
    )
  } else {
    const errorPayload = await runResponse.json()
    assert(runResponse.status() === 400, `Expected graceful provider failure, got HTTP ${runResponse.status()}`)
    assert(String(errorPayload.message || '').includes('LLM provider request failed'), `Unexpected provider failure ${JSON.stringify(errorPayload)}`)
  }

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log('PASS chatflow resource context e2e')
} finally {
  await browser.close()
}
