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
const page = await browser.newPage()

try {
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `015.5 LLM Information Collection ${Date.now()}`,
        description: 'mimo v2 flash information collection smoke',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: { outputVariables: ['sys.query'] } },
          {
            nodeKey: 'info_1',
            type: 'INFORMATION_COLLECTION',
            name: '信息收集',
            config: {
              inputSource: '{{start.sys.query}}',
              outputVariable: 'travel',
              collectionKey: 'travel',
              extractorMode: 'llm',
              includeHistory: false,
              maxRounds: 2,
              streamOutput: 'disabled',
              fields: [
                { name: 'destination', type: 'string', required: true, description: '目的城市' },
                { name: 'budget', type: 'string', required: true, description: '预算金额' },
              ],
            },
          },
          {
            nodeKey: 'end',
            type: 'END',
            name: '结束',
            config: { outputVariable: 'final', output: '{{info_1.destination}}|{{info_1.budget}}' },
          },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'info_1', condition: null },
          { sourceNodeKey: 'info_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create llm information collection chatflow',
  )

  const startedAt = Date.now()
  const result = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
      data: { input: { 'sys.query': '我想预订去上海的旅行，预算是5000元。' } },
      timeout: 60000,
    }),
    'run llm information collection',
  )
  const elapsedMs = Date.now() - startedAt
  if (result.status === 'SUCCEEDED') {
    assert(String(result.output.final).includes('上海'), `Expected destination from LLM, got ${JSON.stringify(result.output)}`)
    assert(String(result.output.final).includes('5000'), `Expected budget from LLM, got ${JSON.stringify(result.output)}`)
  } else {
    assert(result.status === 'INTERRUPTED', `Expected SUCCEEDED or graceful INTERRUPTED, got ${result.status}`)
    assert(
      result.output?.interrupt?.type === 'INFORMATION_COLLECTION',
      `Expected information collection interrupt, got ${JSON.stringify(result.output)}`,
    )
  }

  console.log(JSON.stringify({ status: 'PASS', chatflowId: chatflow.id, elapsedMs, output: result.output }))
} finally {
  await browser.close()
}
