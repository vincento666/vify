import { chromium } from 'playwright'

const baseUrl = process.env.HIFY_E2E_BASE_URL || 'http://127.0.0.1:5173'
const screenshotPath = process.env.HIFY_E2E_SCREENSHOT

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function unwrap(response, label) {
  if (!response.ok()) {
    const text = await response.text()
    throw new Error(`${label} HTTP ${response.status()}: ${text}`)
  }
  const payload = await response.json()
  assert(payload.code === 200, `${label} API ${payload.message}`)
  return payload.data
}

async function findOpenRouterQwenModel(page) {
  for (let pageNo = 1; pageNo <= 20; pageNo += 1) {
    const providers = await unwrap(
      await page.request.get(`${baseUrl}/api/v1/providers?page=${pageNo}&pageSize=100`),
      'list providers',
    )
    for (const provider of providers.list ?? []) {
      if (!provider.enabled) continue
      if (String(provider.baseUrl || '') !== 'https://openrouter.ai/api/v1') continue
      for (const model of provider.models ?? []) {
        if (model.enabled && String(model.modelId || '') === 'qwen/qwen3.5-9b') {
          return { providerId: provider.id, modelConfigId: model.id }
        }
      }
    }
    if ((providers.list ?? []).length === 0 || pageNo * 100 >= providers.total) break
  }
  throw new Error('OpenRouter qwen/qwen3.5-9b model config is required for runtime v2 UAT')
}

async function waitForRuntime(page, runId, wanted = 'SUCCEEDED', timeoutMs = 60000) {
  const deadline = Date.now() + timeoutMs
  let latest = null
  while (Date.now() < deadline) {
    latest = await unwrap(await page.request.get(`${baseUrl}/api/v1/runtime-runs/${runId}`), `get runtime run ${runId}`)
    if (latest.status === wanted) return latest
    if (['SUCCEEDED', 'FAILED', 'CANCELLED', 'INTERRUPTED'].includes(latest.status) && latest.status !== wanted) {
      throw new Error(`Expected ${wanted} for run ${runId}, got ${JSON.stringify(latest)}`)
    }
    await page.waitForTimeout(500)
  }
  throw new Error(`Timed out waiting for ${wanted} on run ${runId}; latest=${JSON.stringify(latest)}`)
}

function runtimeInput(marker) {
  return {
    'sys.query': marker,
    'sys.conversation_id': `runtime-v2-uat-${marker}`,
    'sys.user_id': 'runtime-v2-uat-user',
    'sys.channel': 'api',
  }
}

async function runLlmConcurrencyUat(page, modelConfigId, stamp) {
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `Runtime V2 LLM Concurrency ${stamp}`,
        description: 'runtime v2 real OpenRouter qwen concurrent UAT',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: {} },
          {
            nodeKey: 'llm_1',
            type: 'LLM',
            name: '大模型',
            config: {
              modelConfigId,
              prompt: 'Reply exactly this token and nothing else: {{start.sys.query}}',
              outputVariable: 'answer',
            },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{llm_1.answer}}' } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'llm_1', condition: null },
          { sourceNodeKey: 'llm_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create llm concurrency chatflow',
  )

  const markers = Array.from({ length: 5 }, (_, index) => `LLM_V2_${stamp}_${index}`)
  const starts = await Promise.all(markers.map(async (marker, index) =>
    unwrap(
      await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
        data: { input: runtimeInput(marker), idempotencyKey: `llm-v2-${stamp}-${index}` },
      }),
      `start llm run ${marker}`,
    ),
  ))
  const results = await Promise.all(starts.map((started) => waitForRuntime(page, started.runId)))
  for (const [index, result] of results.entries()) {
    const outputText = JSON.stringify(result.output || {})
    assert(outputText.includes(markers[index]), `LLM run ${index} should include marker, got ${outputText}`)
    assert(!outputText.includes('LLM mock:'), `LLM run ${index} must not use mock output: ${outputText}`)
    const nodes = await unwrap(await page.request.get(`${baseUrl}/api/v1/runtime-runs/${starts[index].runId}/nodes`), 'list llm nodes')
    const llmNode = nodes.list.find((node) => node.nodeKey === 'llm_1')
    assert(llmNode?.outputs?.__usage?.totalTokens > 0, `LLM node should record provider usage: ${JSON.stringify(llmNode)}`)
  }
  return { chatflow, runId: starts[0].runId }
}

async function runAgentV2Uat(page, modelConfigId, stamp) {
  const agentMarker = `AGENT_V2_${stamp}`
  const agent = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/agents`, {
      data: {
        name: `Runtime V2 Agent Target ${stamp}`,
        description: 'runtime v2 agent call target',
        systemPrompt: `Reply with ${agentMarker} and include the ticket id from the user message.`,
        modelConfigId,
        temperature: 0,
        maxTokens: 128,
        maxContextTurns: 4,
        toolIds: [],
      },
    }),
    'create runtime v2 agent',
  )
  const ticket = `TICKET-${stamp}`
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `Runtime V2 Agent ${stamp}`,
        description: 'runtime v2 agent call UAT',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: {} },
          {
            nodeKey: 'agent_call_1',
            type: 'AGENT_CALL',
            name: '智能体',
            config: {
              targetAgentId: agent.id,
              inputMappings: [
                { name: 'message', valueMode: 'reference', value: `Reply exactly with ${agentMarker} ${ticket}. User says {{start.sys.query}}`, required: true },
                { name: 'query', valueMode: 'reference', value: '{{start.sys.query}}' },
              ],
              outputMappings: [{ source: 'answer', target: 'agentAnswer' }],
              timeoutMs: 60000,
              maxDepth: 3,
            },
          },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{agent_call_1.agentAnswer}}' } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'agent_call_1', condition: null },
          { sourceNodeKey: 'agent_call_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create runtime v2 agent chatflow',
  )
  const started = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
      data: { input: runtimeInput(ticket), idempotencyKey: `agent-v2-${stamp}` },
    }),
    'start runtime v2 agent run',
  )
  const result = await waitForRuntime(page, started.runId)
  const outputText = JSON.stringify(result.output || {})
  assert(outputText.includes(agentMarker), `Agent v2 output should include marker, got ${outputText}`)
  assert(outputText.includes(ticket), `Agent v2 output should include ticket, got ${outputText}`)
  const nodes = await unwrap(await page.request.get(`${baseUrl}/api/v1/runtime-runs/${started.runId}/nodes`), 'list agent nodes')
  const agentNode = nodes.list.find((node) => node.nodeKey === 'agent_call_1')
  assert(agentNode?.status === 'COMPLETED', `Agent node should complete, got ${JSON.stringify(agentNode)}`)
  assert(Number(agentNode?.outputs?.sessionId || 0) > 0, `Agent node should expose session id, got ${JSON.stringify(agentNode)}`)
  return { chatflow, runId: started.runId }
}

async function runConditionV2Uat(page, stamp) {
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `Runtime V2 Condition ${stamp}`,
        description: 'runtime v2 condition UAT',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: {} },
          {
            nodeKey: 'condition_1',
            type: 'CONDITION',
            name: '条件',
            config: {
              outputVariable: 'route',
              branches: [
                { key: 'vip', conditions: [{ left: '{{start.sys.query}}', operator: 'contains', right: 'vip' }] },
              ],
              defaultBranch: 'normal',
            },
          },
          { nodeKey: 'vip_msg', type: 'MESSAGE', name: 'VIP', config: { content: 'vip route', outputVariable: 'content' } },
          { nodeKey: 'normal_msg', type: 'MESSAGE', name: 'Normal', config: { content: 'normal route', outputVariable: 'content' } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: '{{vip_msg.content}}{{normal_msg.content}}' } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'condition_1', condition: null },
          { sourceNodeKey: 'condition_1', targetNodeKey: 'vip_msg', condition: 'vip' },
          { sourceNodeKey: 'condition_1', targetNodeKey: 'normal_msg', condition: null },
          { sourceNodeKey: 'vip_msg', targetNodeKey: 'end', condition: null },
          { sourceNodeKey: 'normal_msg', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create condition chatflow',
  )
  const started = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
      data: { input: runtimeInput(`vip ${stamp}`), idempotencyKey: `condition-v2-${stamp}` },
    }),
    'start condition run',
  )
  const result = await waitForRuntime(page, started.runId)
  assert(result.output?.final === 'vip route', `Condition should select vip branch, got ${JSON.stringify(result.output)}`)
  const nodes = await unwrap(await page.request.get(`${baseUrl}/api/v1/runtime-runs/${started.runId}/nodes`), 'list condition nodes')
  assert(nodes.list.map((node) => node.nodeKey).includes('condition_1'), `Condition node should be recorded: ${JSON.stringify(nodes)}`)
  assert(!nodes.list.map((node) => node.nodeKey).includes('normal_msg'), `Condition should skip default path: ${JSON.stringify(nodes)}`)
  return { chatflow, runId: started.runId }
}

async function runErrorV2Uat(page, stamp) {
  const chatflow = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows`, {
      data: {
        name: `Runtime V2 Error ${stamp}`,
        description: 'runtime v2 failure UAT',
        nodes: [
          { nodeKey: 'start', type: 'START', name: '开始', config: {} },
          { nodeKey: 'message_1', type: 'MESSAGE', name: '消息', config: { raiseError: `uat failure ${stamp}` } },
          { nodeKey: 'end', type: 'END', name: '结束', config: { outputVariable: 'final', output: 'never' } },
        ],
        edges: [
          { sourceNodeKey: 'start', targetNodeKey: 'message_1', condition: null },
          { sourceNodeKey: 'message_1', targetNodeKey: 'end', condition: null },
        ],
      },
    }),
    'create error chatflow',
  )
  const started = await unwrap(
    await page.request.post(`${baseUrl}/api/v1/chatflows/${chatflow.id}/runs`, {
      data: { input: runtimeInput(`error ${stamp}`), idempotencyKey: `error-v2-${stamp}` },
    }),
    'start error run',
  )
  const failed = await waitForRuntime(page, started.runId, 'FAILED')
  assert(String(failed.error || '').includes(`uat failure ${stamp}`), `Failure should expose error, got ${JSON.stringify(failed)}`)
  const events = await unwrap(await page.request.get(`${baseUrl}/api/v1/runtime-runs/${started.runId}/events`), 'list error events')
  assert(events.list.some((event) => event.type === 'workflow_node_failed'), `Failure event should be recorded: ${JSON.stringify(events)}`)
  return { chatflow, runId: started.runId }
}

const browser = await chromium.launch({
  headless: process.env.HIFY_E2E_HEADED !== '1',
  slowMo: process.env.HIFY_E2E_HEADED === '1' ? 120 : 0,
})
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })

try {
  const stamp = Date.now()
  const { modelConfigId } = await findOpenRouterQwenModel(page)
  const llm = await runLlmConcurrencyUat(page, modelConfigId, stamp)
  const agent = await runAgentV2Uat(page, modelConfigId, stamp)
  const condition = await runConditionV2Uat(page, stamp)
  const failure = await runErrorV2Uat(page, stamp)

  await page.goto(`${baseUrl}/chatflows/${condition.chatflow.id}/canvas?debug=1&runId=${condition.runId}&runtime=v2`, { waitUntil: 'networkidle' })
  const dock = page.getByTestId('workflow-debug-dock')
  await dock.getByText('condition_1', { exact: true }).first().waitFor({ state: 'visible', timeout: 10000 })
  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true })
  }

  console.log(`PASS runtime v2 production node uat llm=${llm.runId} agent=${agent.runId} condition=${condition.runId} failure=${failure.runId}`)
} finally {
  await browser.close()
}
