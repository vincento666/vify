import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  if (!response.ok()) {
    const text = await response.text()
    throw new Error(`${label} HTTP ${response.status()} ${text}`)
  }
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function findEnabledModel(page) {
  let fallbackModelId = null
  for (let pageNo = 1; pageNo <= 20; pageNo += 1) {
    const providers = await unwrap(
      await page.request.get(`${baseUrl}/api/v1/providers?page=${pageNo}&pageSize=100`),
      'list providers',
    )
    for (const provider of providers.list ?? []) {
      if (!provider.enabled) continue
      for (const model of provider.models ?? []) {
        if (!model.enabled) continue
        if (String(provider.baseUrl || '').startsWith('mock://success')) return model.id
        fallbackModelId ??= model.id
      }
    }
    if ((providers.list ?? []).length === 0 || pageNo * 100 >= providers.total) break
  }
  if (fallbackModelId) return fallbackModelId
  throw new Error('No enabled model found for workflow node evidence e2e')
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const stamp = Date.now()
  const modelConfigId = await findEnabledModel(page)
  const workflow = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows`, {
    data: {
      name: `024.2 Node Evidence ${stamp}`,
      description: 'node evidence debug detail e2e',
      nodes: [
        { nodeKey: 'start', type: 'START', name: '开始', config: { ui: { position: { x: 120, y: 180 } } } },
        {
          nodeKey: 'llm_1',
          type: 'LLM',
          name: '大模型',
          config: {
            modelConfigId,
            prompt: 'Summarize {{start.USER_INPUT}}',
            outputVariable: 'answer',
            ui: { position: { x: 460, y: 180 } },
          },
        },
        {
          nodeKey: 'end',
          type: 'END',
          name: '结束',
          config: {
            outputVariable: 'final',
            output: '{{llm_1.answer}}',
            ui: { position: { x: 820, y: 180 } },
          },
        },
      ],
      edges: [
        { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
        { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
      ],
    },
  }), 'create workflow')

  const run = await unwrap(await page.request.post(`${baseUrl}/api/v1/workflows/${workflow.id}/runs`, {
    data: { input: { USER_INPUT: 'node evidence payload' } },
  }), 'run workflow')

  const debug = await unwrap(await page.request.get(`${baseUrl}/api/v1/workflows/${workflow.id}/runs/${run.runId}/debug`), 'debug detail')
  const llmDetail = debug.nodeDetails.find((node) => node.nodeKey === 'llm_1')
  assert(llmDetail, `Expected LLM node detail: ${JSON.stringify(debug.nodeDetails)}`)
  assert(llmDetail.totalTokens >= llmDetail.outputTokens, `Expected token evidence: ${JSON.stringify(llmDetail)}`)
  assert(llmDetail.resourceType === 'LLM', `Expected LLM resource type: ${JSON.stringify(llmDetail)}`)
  assert(llmDetail.outputSummary.includes('answer'), `Expected output summary: ${JSON.stringify(llmDetail)}`)
  assert(String(JSON.stringify(llmDetail.inputs || {})).includes('node evidence payload'), `Expected node input detail: ${JSON.stringify(llmDetail)}`)
  assert(String(JSON.stringify(llmDetail.outputs || {})).includes('answer'), `Expected node output detail: ${JSON.stringify(llmDetail)}`)

  await page.goto(`${baseUrl}/workflows/${workflow.id}/canvas?runId=${run.runId}&debug=1`, { waitUntil: 'networkidle' })
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.getByText('调试详情', { exact: true }).waitFor({ state: 'visible', timeout: 8000 })
  await dock.getByTestId('workflow-run-call-tree').getByRole('button', { name: /llm_1/ }).click()
  const evidence = dock.getByTestId('workflow-node-evidence-row').first()
  await evidence.waitFor({ state: 'visible', timeout: 8000 })
  const evidenceText = await evidence.innerText()
  assert(evidenceText.includes('Tokens'), `Expected tokens in evidence row, got: ${evidenceText}`)
  assert(evidenceText.includes('Cost'), `Expected cost in evidence row, got: ${evidenceText}`)
  assert(evidenceText.includes('ms'), `Expected latency in evidence row, got: ${evidenceText}`)
  assert(evidenceText.includes('LLM'), `Expected resource type in evidence row, got: ${evidenceText}`)
  const nodeDetailText = await dock.getByTestId('workflow-run-node-details').innerText()
  assert(nodeDetailText.includes('输入'), `Expected input section in node detail, got: ${nodeDetailText}`)
  assert(nodeDetailText.includes('node evidence payload'), `Expected rendered input payload in node detail, got: ${nodeDetailText}`)
  assert(nodeDetailText.includes('输出'), `Expected output section in node detail, got: ${nodeDetailText}`)
  assert(nodeDetailText.includes('answer'), `Expected output answer in node detail, got: ${nodeDetailText}`)

  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS workflow node evidence detail e2e workflow=${workflow.id} run=${run.runId}`)
} finally {
  await browser.close()
}
